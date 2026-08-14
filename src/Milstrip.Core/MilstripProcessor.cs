using System.Net;
using System.Text.RegularExpressions;

namespace Milstrip.Core;

public sealed record ProcessingIssue(string Code, string Message, string Severity);

public sealed record MilstripFields(
    string SourceLine, string Dic, string Ric, string MediaStatusCode,
    string StockOrPartNumber, string UnitOfIssue, string OrderQuantityRaw,
    string Requisition, string Suffix, string SupplementaryAddress,
    string SignalCode, string FundCode, string DistributionCode,
    string ProjectCode, string PriorityCode, string RequiredDeliveryDate,
    string AdviceCode, string Tail67To69, string OwnershipCode,
    string ConditionCode, string Tail72To73, string Tail74To80)
{
    public string FamilyGroup => Regex.IsMatch(Dic, "^A2[A-Z0-9]$") ? "A2"
        : Regex.IsMatch(Dic, "^A5[A-Z0-9]$") || Dic == "AF6" ? "A5_AF6" : "UNKNOWN";
    public string Nsn => StockOrPartNumber.TrimEnd() is var value
        && value.Length == 13 && value.All(IsAsciiDigit) ? value : "";
    public string ErpOrder => (Requisition + (string.IsNullOrWhiteSpace(Suffix) ? "" : Suffix)).TrimEnd();
    public string EffectiveDodaac => SignalCode.Length > 0 && string.CompareOrdinal(SignalCode, "J") < 0
        ? Requisition[..Math.Min(6, Requisition.Length)] : SupplementaryAddress;
    public bool IsA5E => Dic == "A5E";
    private static bool IsAsciiDigit(char value) => value is >= '0' and <= '9';
}

public sealed record MilstripRecord(
    string RawLine, string CleanedLine, MilstripFields Fields,
    IReadOnlyList<ProcessingIssue> Issues, string? Canonical)
{
    public bool HasErrors => Issues.Any(issue => issue.Severity == "ERROR");
    public string Status => HasErrors ? "REJECTED"
        : Issues.Any(issue => issue.Severity == "WARNING") ? "REQUIRES_REVIEW" : "VALID";
}

public static partial class MilstripProcessor
{
    public const int RecordLength = 80;
    public const int MinimumStructuralLength = 71;

    private static readonly (int Start, int Length)[] FieldPositions =
    [
        (1,3), (4,3), (7,1), (8,15), (23,2), (25,5), (30,14), (44,1),
        (45,6), (51,1), (52,2), (54,3), (57,3), (60,2), (62,3), (65,2),
        (67,3), (70,1), (71,1), (72,2), (74,7)
    ];

    public static IReadOnlyList<MilstripRecord> ProcessText(string rawText)
    {
        var records = new List<MilstripRecord>();
        foreach (var (rawLine, cleanedLine) in ExtractCandidates(rawText))
        {
            var normalized = NormalizeLine(cleanedLine);
            var normalizationIssues = new List<ProcessingIssue>();
            var expansions = PlaceholderExpansions(normalized);
            var hasPunctuation = normalized.Contains('.') || normalized.Contains('…');
            if (hasPunctuation && expansions.Count == 0)
                normalizationIssues.Add(Issue("MIL-NORM-002", "Dot/ellipsis punctuation does not match the collected repair pattern. The record was not altered; correct it manually or supply more evidence.", "ERROR"));
            else if (expansions.Count > 0)
            {
                var valid = expansions.Where(candidate => !ValidateRecord(candidate, ParseFields(candidate)).Any(i => i.Severity == "ERROR")).ToList();
                if (valid.Count == 1)
                {
                    normalized = valid[0];
                    normalizationIssues.Add(Issue("MIL-NORM-001", "Dot/ellipsis spacing contamination was repaired using the only interpretation that satisfies the fixed-width contract. Review the canonical record before submission.", "WARNING"));
                }
                else
                    normalizationIssues.Add(Issue("MIL-NORM-002", $"Dot/ellipsis spacing is ambiguous ({(valid.Count == 0 ? "no valid" : "multiple valid")} interpretations). The record was not repaired; obtain clarification or correct it manually.", "ERROR"));
            }

            var fields = ParseFields(normalized);
            var issues = normalizationIssues.Concat(ValidateRecord(normalized, fields)).ToList();
            var canonical = issues.Any(i => i.Severity == "ERROR") ? null : BuildCanonical(fields);
            records.Add(new(rawLine, normalized, fields, issues, canonical));
        }
        return records;
    }

    public static IReadOnlyList<(string RawLine, string CleanedLine)> ExtractCandidates(string rawText)
    {
        var text = StripHtml(rawText);
        var result = new List<(string, string)>();
        foreach (var line in text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n'))
        {
            var cleaned = CleanLine(line.TrimStart('\ufeff'));
            var candidate = cleaned.TrimStart(' ', '\ufeff');
            if (Regex.IsMatch(candidate, "^(?:A2|A5|AF6)", RegexOptions.IgnoreCase)) result.Add((line, cleaned));
        }
        return result;
    }

    // A small deterministic tokenizer is preferable to a tag regex here: an HTML
    // attribute may legally contain '>', and treating it as the tag terminator can
    // leak markup into a candidate or split its fixed-width payload.
    public static string StripHtml(string input)
    {
        var output = new System.Text.StringBuilder(input.Length);
        for (var index = 0; index < input.Length;)
        {
            if (input[index] != '<')
            {
                var next = input.IndexOf('<', index);
                if (next < 0) next = input.Length;
                output.Append(WebUtility.HtmlDecode(input[index..next]));
                index = next;
                continue;
            }

            var end = FindTagEnd(input, index + 1);
            if (end < 0)
            {
                output.Append(WebUtility.HtmlDecode(input[index..]));
                break;
            }
            var tag = input[(index + 1)..end].TrimStart();
            if (tag.StartsWith('/')) tag = tag[1..].TrimStart();
            var nameLength = 0;
            while (nameLength < tag.Length && char.IsAsciiLetterOrDigit(tag[nameLength])) nameLength++;
            var name = tag[..nameLength];
            if (name.Equals("br", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("p", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("div", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("li", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("tr", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("table", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("section", StringComparison.OrdinalIgnoreCase) ||
                name.Equals("article", StringComparison.OrdinalIgnoreCase)) output.Append('\n');
            index = end + 1;
        }
        return output.ToString();
    }

    public static string CleanLine(string line) => line.Replace('\u00a0', ' ').Replace('\t', ' ')
        .Replace('\u200b', ' ').TrimStart(' ').TrimEnd('\r', '\n');

    public static string NormalizeLine(string line)
    {
        var chars = line.ToCharArray();
        for (var index = 0; index < chars.Length; index++)
            if (chars[index] is >= 'a' and <= 'z') chars[index] = (char)(chars[index] - 32);
        return new(chars);
    }

    public static MilstripFields ParseFields(string line)
    {
        var v = FieldPositions.Select(position => Slice(line, position.Start, position.Length)).ToArray();
        return new(line, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], v[9],
            v[10], v[11], v[12], v[13], v[14], v[15], v[16], v[17], v[18], v[19], v[20]);
    }

    public static string BuildCanonical(MilstripFields fields)
    {
        if (fields.SourceLine.Length > RecordLength) throw new ArgumentException($"Cannot canonicalize {fields.SourceLine.Length} characters into an 80-character record");
        if (fields.SourceLine.Any(ch => ch is < (char)0x20 or > (char)0x7e)) throw new ArgumentException("Canonical MILSTRIP must contain printable ASCII only");
        return fields.SourceLine.PadRight(RecordLength);
    }

    public static IReadOnlyList<ProcessingIssue> ValidateRecord(string line, MilstripFields f)
    {
        var issues = new List<ProcessingIssue>();
        if (line.Length < MinimumStructuralLength) issues.Add(Issue("MIL-STR-002", $"Record is {line.Length} characters; at least {MinimumStructuralLength} are required to contain every known field up to and including the condition code. Likely truncated during copy/paste.", "ERROR"));
        else if (line.Length > RecordLength) issues.Add(Issue("MIL-STR-005", $"Record is {line.Length} characters; maximum is {RecordLength}. Extra characters will not be truncated.", "ERROR"));
        if (line.Any(ch => ch is < (char)0x20 or > (char)0x7e)) issues.Add(Issue("MIL-STR-006", "Record contains non-ASCII or non-printable characters after transport cleanup.", "ERROR"));
        if (issues.Any(i => i.Severity == "ERROR")) return issues;

        if (f.FamilyGroup == "UNKNOWN") issues.Add(Issue("MIL-STR-001", $"Unrecognized record family {PythonRepr(f.Dic)}. DLM layouts supported: A2_, A5_, AF6.", "ERROR"));
        var stock = f.StockOrPartNumber.TrimEnd();
        if (stock.Length == 0) issues.Add(Issue("MIL-STR-003", "Stock or Part Number (positions 8-22) is blank.", "ERROR"));
        else if (stock.All(IsAsciiDigit) && stock.Length != 13) issues.Add(Issue("MIL-STR-003", $"A numeric NSN must be exactly 13 digits; received {stock.Length}. Do not guess or remove a digit—obtain the corrected NSN from DLA.", "ERROR"));
        else if (!Regex.IsMatch(stock, "^[A-Z0-9 -]{1,15}$")) issues.Add(Issue("MIL-STR-003", $"Stock or Part Number contains unsupported characters: {PythonRepr(stock)}.", "ERROR"));
        if (string.IsNullOrWhiteSpace(f.Requisition)) issues.Add(Issue("MIL-STR-004", "Requisition/document number is blank.", "ERROR"));
        AddQuantityIssue(f, issues);
        if (!Regex.IsMatch(f.PriorityCode, "^[0-9]{2}$")) issues.Add(Issue("MIL-SEM-002", $"Priority must be numeric. Received {PythonRepr(f.PriorityCode)}.", "ERROR"));
        else if (int.Parse(f.PriorityCode) is < 1 or > 15) issues.Add(Issue("MIL-SEM-002", $"Priority must be between 01 and 15. Received {PythonRepr(f.PriorityCode)}.", "ERROR"));
        if (string.IsNullOrWhiteSpace(f.ConditionCode)) issues.Add(Issue("MIL-SEM-003", "Condition code is blank — Shawn Hinkle flagged this field as critical (maps to inventory status).", "ERROR"));
        if (f.FamilyGroup == "A2" && !string.IsNullOrWhiteSpace(f.Tail67To69) && f.Tail67To69 != "SMS" && !Regex.IsMatch(f.Tail67To69, "^[0-9]{3}$")) issues.Add(Issue("MIL-STR-007", $"A2 positions 67-69 are misaligned or unsupported: {PythonRepr(f.Tail67To69)}. Expected blank/date-of-receipt per DLM or the observed Travis 'SMS' variant.", "ERROR"));
        if (string.IsNullOrWhiteSpace(f.SignalCode)) issues.Add(Issue("MIL-SEM-004", "Signal code is blank — this field determines the effective ship-to DODAAC and cannot be inferred.", "ERROR"));
        else if (string.IsNullOrWhiteSpace(f.EffectiveDodaac)) issues.Add(Issue("MIL-SEM-005", "Signal code selects an empty effective DODAAC; the destination cannot be inferred.", "ERROR"));
        if (f.IsA5E) issues.Add(Issue("MIL-BIZ-001", "A5E record — a ship-to address must be supplied out-of-band before submission (cannot be derived from the MILSTRIP text). Confirmed by Shawn Hinkle on the 2026-08-12 call.", "WARNING"));
        if (f.FamilyGroup == "A2" && f.Tail67To69 == "SMS") issues.Add(Issue("MIL-BIZ-002", "Legacy Travis A2 variant carries 'SMS' at positions 67-69, while DLM AP8.25 defines those positions as date of receipt. Preserved without reinterpretation.", "INFO"));
        if (!string.IsNullOrWhiteSpace(f.Tail74To80)) issues.Add(Issue("MIL-BIZ-003", $"Positions 74-80 carry {PythonRepr(f.Tail74To80)} ({(f.FamilyGroup == "A5_AF6" ? "unit price" : "RIC From/inventory control")} under the applicable DLM layout). Preserved; the current legacy SQL does not consume it directly.", "INFO"));
        if (f.Dic == "AF6") issues.Add(Issue("MIL-BIZ-004", "AF6 is recognized by DLM AP8.12, but its behavior through the current Travis SQL prototype has not been verified; submission support requires a decision.", "WARNING"));
        if (f.FamilyGroup != "UNKNOWN" && f.Dic is not ("A2A" or "A5A" or "A5E" or "AF6")) issues.Add(Issue("MIL-BIZ-005", $"DIC {PythonRepr(f.Dic)} matches a DLM layout group but has not been observed in Travis production evidence; confirm before submission.", "WARNING"));
        if (f.OrderQuantityRaw.EndsWith('M')) issues.Add(Issue("MIL-BIZ-006", "The DLM 'M' quantity form is structurally valid, but the current Travis SQL casts positions 25-29 to INT and cannot consume it unchanged.", "WARNING"));
        return issues;
    }

    private static void AddQuantityIssue(MilstripFields fields, List<ProcessingIssue> issues)
    {
        var raw = fields.OrderQuantityRaw;
        if (Regex.IsMatch(raw, "^[0-9]{5}$"))
        {
            if (int.Parse(raw) <= 0) issues.Add(Issue("MIL-SEM-001", "Quantity must be greater than zero.", "ERROR"));
            return;
        }
        if (Regex.IsMatch(raw, "^[0-9]{4}M$") && !ValidQuantity(fields))
        {
            issues.Add(Issue("MIL-SEM-001", "Quantity suffix 'M' is allowed only for the ammunition/FSC categories listed by DLM AP8.12/AP8.25.", "ERROR"));
            return;
        }
        if (!Regex.IsMatch(raw, "^[0-9]{4}M$")) issues.Add(Issue("MIL-SEM-001", $"Quantity must be five ASCII digits, or four digits plus an allowed 'M'. Received {PythonRepr(raw)}.", "ERROR"));
    }

    private static bool ValidQuantity(MilstripFields fields)
    {
        var raw = fields.OrderQuantityRaw;
        if (Regex.IsMatch(raw, "^[0-9]{5}$")) return int.Parse(raw) > 0;
        if (!Regex.IsMatch(raw, "^[0-9]{4}M$") || int.Parse(raw[..4]) < 100) return false;
        var stock = fields.StockOrPartNumber.Trim();
        return stock.StartsWith("13", StringComparison.Ordinal) || new[] { "1410", "1420", "1427", "1440", "5330", "5865", "6810", "8140" }.Contains(stock[..Math.Min(4, stock.Length)]);
    }

    private static IReadOnlyList<string> PlaceholderExpansions(string line)
    {
        var match = DotEmailShape().Match(line);
        if (!match.Success) return [];
        var g = match.Groups;
        var candidate = g["prefix"].Value + g["stock"].Value.PadRight(15) + g["ui"].Value + g["qty"].Value +
            g["req"].Value + " " + g["supp"].Value + g["signal"].Value + g["fund"].Value + "   " +
            g["middle"].Value + "  " + g["tail"].Value;
        return [candidate];
    }

    private static string Slice(string value, int start, int length) => start - 1 < value.Length
        ? value.Substring(start - 1, Math.Min(length, value.Length - start + 1)) : "";
    private static bool IsAsciiDigit(char value) => value is >= '0' and <= '9';
    private static ProcessingIssue Issue(string code, string message, string severity) => new(code, message, severity);
    private static string PythonRepr(string value) => "'" + value.Replace("\\", "\\\\").Replace("'", "\\'") + "'";
    private static int FindTagEnd(string input, int start)
    {
        char quote = '\0';
        for (var index = start; index < input.Length; index++)
        {
            var current = input[index];
            if (quote == '\0' && current is '\'' or '"') quote = current;
            else if (current == quote) quote = '\0';
            else if (quote == '\0' && current == '>') return index;
        }
        return -1;
    }
    [GeneratedRegex(@"^(?<prefix>A2[A-Z0-9][A-Z0-9]{3}[A-Z0-9])(?<stock>[A-Z0-9-]{1,15})\.\.(?<ui>[A-Z]{2})(?<qty>[0-9]{5})(?<req>[A-Z0-9]{14})\.(?<supp>[A-Z0-9]{6})(?<signal>[A-Z0-9])(?<fund>[A-Z0-9]{2})…(?<middle>[A-Z0-9]{8})…(?<tail>SMSAA)\s*$")]
    private static partial Regex DotEmailShape();
}
