using Milstrip.Core;

var fixtures = new[]
{
    ("A2ASTZ08405015308058  EA00140SL470151000BAJ SC0140MKK      03103  SMSAA  0001657", "SL470151000BAJ", "8405015308058", "00140", "03", "VALID"),
    ("A2ASTZ08405015308058  EA00340SL470151000BCG SC1143MKK      03103  SMSAA  0001657", "SL470151000BCG", "8405015308058", "00340", "03", "VALID"),
    ("A2ASTZ08405015308034  EA00050SL470151000BDC SC1143MKK      03103  SMSAA", "SL470151000BDC", "8405015308034", "00050", "03", "VALID"),
    ("A5ASTZS8405012795607  EA00084SL470150160BYS SC1143MKK   RDO03999  SMSAA  0016489", "SL470150160BYS", "8405012795607", "00084", "03", "VALID"),
    ("A5ESTZS7210001195335  EA01500SC010050162200 SC0101M00   HSI06035  SMSAA  0000465", "SC010050162200", "7210001195335", "01500", "06", "REQUIRES_REVIEW"),
    ("A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA      ", "SL470162240DCV", "8405016819440", "00520", "15", "VALID"),
    ("A2ASTZ08405016819460  EA00420SL470162240DDL SC0141MKK      15     SMSAA      ", "SL470162240DDL", "8405016819460", "00420", "15", "VALID"),
    ("A2ASTZ08405016819468  EA00300SL470162240DDQ SC0141MKK      15     SMSAA      ", "SL470162240DDQ", "8405016819468", "00300", "15", "VALID"),
    ("A2ASTZ08405016819531  EA00140SL470162240DDT SC0141MKK      15     SMSAA      ", "SL470162240DDT", "8405016819531", "00140", "15", "VALID"),
    ("A5ASTZS7210014980306  EA00001V216876209S111 YNSS01ASE 9BEP502999  SMSAA", "V216876209S111", "7210014980306", "00001", "02", "VALID")
};

var failures = new List<string>();
var expectedIssues = new[]
{
    new[] { "MIL-BIZ-002:INFO", "MIL-BIZ-003:INFO" }, new[] { "MIL-BIZ-002:INFO", "MIL-BIZ-003:INFO" },
    new[] { "MIL-BIZ-002:INFO" }, new[] { "MIL-BIZ-003:INFO" },
    new[] { "MIL-BIZ-001:WARNING", "MIL-BIZ-003:INFO" }, new[] { "MIL-BIZ-002:INFO" },
    new[] { "MIL-BIZ-002:INFO" }, new[] { "MIL-BIZ-002:INFO" },
    new[] { "MIL-BIZ-002:INFO" }, Array.Empty<string>()
};
for (var fixtureIndex = 0; fixtureIndex < fixtures.Length; fixtureIndex++)
{
    var expected = fixtures[fixtureIndex];
    var record = MilstripProcessor.ProcessText(expected.Item1).Single();
    Check(record.Fields.ErpOrder == expected.Item2, "ERP order", failures);
    Check(record.Fields.Nsn == expected.Item3, "NSN", failures);
    Check(record.Fields.OrderQuantityRaw == expected.Item4, "quantity", failures);
    Check(record.Fields.PriorityCode == expected.Item5, "priority", failures);
    Check(record.Status == expected.Item6, "status", failures);
    Check(record.Canonical == expected.Item1.PadRight(80), "exact canonical", failures);
    Check(record.Canonical is not null && SameFields(record.Fields, MilstripProcessor.ParseFields(record.Canonical)), "all-field round trip", failures);
    Check(record.Issues.Select(i => $"{i.Code}:{i.Severity}").SequenceEqual(expectedIssues[fixtureIndex]), "issue order", failures);
}

var html = $"<p>{fixtures[0].Item1}</p><br>{fixtures[1].Item1}";
Check(MilstripProcessor.ProcessText(html).Count == 2, "HTML extraction", failures);
var quotedGtHtml = $"<p title=\"x > y\">{fixtures[0].Item1}</p>";
Check(MilstripProcessor.ProcessText(quotedGtHtml).Single().Canonical == fixtures[0].Item1.PadRight(80), "quoted > HTML attribute", failures);
Check(MilstripProcessor.ProcessText("A2ASTZ084050").Single().Status == "REJECTED", "truncation rejection", failures);
var repaired = MilstripProcessor.ProcessText("A2ASTZS8405012345678..EA00010AA000000000002.ZZ9999MKK…RDO03999…SMSAA ").Single();
Check(repaired.Status == "REQUIRES_REVIEW" && repaired.Issues.Any(i => i.Code == "MIL-NORM-001"), "evidence-backed repair", failures);
var unsafeRepair = MilstripProcessor.ProcessText("A2A…").Single();
Check(unsafeRepair.Status == "REJECTED" && unsafeRepair.Canonical is null, "ambiguous repair rejection", failures);

var baseline = fixtures[0].Item1;
AssertIssues(baseline + "X", new[] { "MIL-STR-005:ERROR" }, ">80", failures);
AssertIssues("A2ASTZS84050123456789..EA00004AA000000000001.ZZ9999MKK…RDO03999…SMSAA ",
    new[] { "MIL-NORM-002:ERROR", "MIL-STR-002:ERROR", "MIL-STR-006:ERROR" }, "14 digit contaminated", failures);
AssertHasIssue(SetField(baseline, 25, 5, "00000"), "MIL-SEM-001:ERROR", "zero quantity", failures);
AssertHasIssue(SetField(baseline, 25, 5, "12X45"), "MIL-SEM-001:ERROR", "nonnumeric quantity", failures);
AssertHasIssue(SetField(baseline, 60, 2, "16"), "MIL-SEM-002:ERROR", "priority range", failures);
AssertHasIssue(SetField(baseline, 60, 2, "A1"), "MIL-SEM-002:ERROR", "priority numeric", failures);
AssertHasIssue(SetField(baseline, 8, 15, ""), "MIL-STR-003:ERROR", "blank stock", failures);
AssertHasIssue(SetField(baseline, 30, 14, ""), "MIL-STR-004:ERROR", "blank requisition", failures);
AssertHasIssue(SetField(baseline, 51, 1, ""), "MIL-SEM-004:ERROR", "blank signal", failures);
AssertHasIssue(SetField(baseline, 71, 1, ""), "MIL-SEM-003:ERROR", "blank condition", failures);
AssertHasIssue("AF6" + baseline[3..], "MIL-BIZ-004:WARNING", "AF6", failures);
AssertHasIssue("A2B" + baseline[3..], "MIL-BIZ-005:WARNING", "unobserved DIC", failures);
AssertHasIssue(SetField(baseline, 8, 15, "84050153080é8"), "MIL-STR-006:ERROR", "Unicode", failures);
Check(MilstripProcessor.ProcessText("\ufeff   " + baseline.ToLowerInvariant()).Single().Canonical == baseline.PadRight(80), "BOM lowercase", failures);
Check(MilstripProcessor.ProcessText(baseline.Replace(" ", "\u00a0", StringComparison.Ordinal)).Count == 1, "NBSP", failures);
Check(MilstripProcessor.ProcessText(baseline.Replace(" ", "\t", StringComparison.Ordinal)).Count == 1, "tabs", failures);
Check(MilstripProcessor.ProcessText("Hello\nNo orders here").Count == 0, "no candidates", failures);
Check(MilstripProcessor.ProcessText(baseline + "\n" + fixtures[1].Item1).Count == 2, "multiple orders", failures);

if (failures.Count > 0)
{
    Console.Error.WriteLine($"Parity failures ({failures.Count}): {string.Join(", ", failures)}");
    return 1;
}
Console.WriteLine($"PASS: {fixtures.Length} golden records plus extraction, rejection, and normalization scenarios.");
return 0;

static void Check(bool condition, string name, List<string> failures)
{
    if (!condition) failures.Add(name);
}

static void AssertIssues(string line, string[] expected, string name, List<string> failures)
{
    var actual = MilstripProcessor.ProcessText(line).Single().Issues.Select(i => $"{i.Code}:{i.Severity}").ToArray();
    Check(actual.SequenceEqual(expected), $"{name} [{string.Join(",", actual)}]", failures);
}

static void AssertHasIssue(string line, string expected, string name, List<string> failures)
{
    var actual = MilstripProcessor.ProcessText(line).Single().Issues.Select(i => $"{i.Code}:{i.Severity}");
    Check(actual.Contains(expected), name, failures);
}

static string SetField(string line, int start, int length, string value) =>
    line[..(start - 1)] + value[..Math.Min(value.Length, length)].PadRight(length) + line[Math.Min(line.Length, start - 1 + length)..];

static bool SameFields(MilstripFields left, MilstripFields right)
{
    static string N(string value) => value.TrimEnd();
    return N(left.Dic) == N(right.Dic) && N(left.Ric) == N(right.Ric) && N(left.MediaStatusCode) == N(right.MediaStatusCode) &&
        N(left.StockOrPartNumber) == N(right.StockOrPartNumber) && N(left.UnitOfIssue) == N(right.UnitOfIssue) &&
        N(left.OrderQuantityRaw) == N(right.OrderQuantityRaw) && N(left.Requisition) == N(right.Requisition) &&
        N(left.Suffix) == N(right.Suffix) && N(left.SupplementaryAddress) == N(right.SupplementaryAddress) &&
        N(left.SignalCode) == N(right.SignalCode) && N(left.FundCode) == N(right.FundCode) &&
        N(left.DistributionCode) == N(right.DistributionCode) && N(left.ProjectCode) == N(right.ProjectCode) &&
        N(left.PriorityCode) == N(right.PriorityCode) && N(left.RequiredDeliveryDate) == N(right.RequiredDeliveryDate) &&
        N(left.AdviceCode) == N(right.AdviceCode) && N(left.Tail67To69) == N(right.Tail67To69) &&
        N(left.OwnershipCode) == N(right.OwnershipCode) && N(left.ConditionCode) == N(right.ConditionCode) &&
        N(left.Tail72To73) == N(right.Tail72To73) && N(left.Tail74To80) == N(right.Tail74To80);
}
