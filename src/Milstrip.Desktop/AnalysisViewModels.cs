namespace Milstrip.Desktop;

internal sealed record AnalysisRow(
    int Number,
    string Status,
    string ErpOrder,
    string EffectiveDodaac,
    string NationalStockNumber,
    string Quantity,
    string Canonical,
    IReadOnlyList<string> Issues);

internal interface IAnalysisAdapter
{
    IReadOnlyList<AnalysisRow> Analyze(string input);
}
