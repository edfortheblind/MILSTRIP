using Milstrip.Core;

namespace Milstrip.Desktop;

internal sealed class CoreAnalysisAdapter : IAnalysisAdapter
{
    public IReadOnlyList<AnalysisRow> Analyze(string input) =>
        MilstripProcessor.ProcessText(input)
            .Select((record, index) => new AnalysisRow(
                index + 1,
                record.Status,
                record.Fields.ErpOrder,
                record.Fields.EffectiveDodaac,
                record.Fields.Nsn,
                record.Fields.OrderQuantityRaw,
                record.Canonical ?? string.Empty,
                record.Issues.Select(issue => $"[{issue.Severity}] {issue.Code}: {issue.Message}").ToArray()))
            .ToArray();
}
