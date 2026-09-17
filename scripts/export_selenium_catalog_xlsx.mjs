import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) {
    throw new Error(`missing required argument ${name}`);
  }
  return process.argv[index + 1];
}

function optionalArgument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}

const inputPath = argument("--input");
const outputPath = argument("--output");
const previewDirectory = optionalArgument("--preview-directory");
const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
const records = payload.records;
if (!Array.isArray(records) || records.length === 0) {
  throw new Error("input must contain at least one record");
}

const columns = [
  ["Source record ID", "source_record_id"],
  ["Release year", "release_year"],
  ["Brand", "brand"],
  ["Toy number", "toy_number"],
  ["Collector number", "collector_number"],
  ["Source model label", "source_model_label"],
  ["Casting name", "casting_name"],
  ["Variant note", "variant_note"],
  ["Series", "series"],
  ["Series position", "series_position"],
  ["Color", "color"],
  ["Source page title", "source_page_title"],
  ["Source page URL", "source_page_url"],
  ["Source table", "source_table_index"],
  ["Source row", "source_row"],
  ["Parse status", "parse_status"],
  ["Parse error", "parse_error"],
  ["Collected at (UTC)", "scraped_at_utc"],
  ["Raw fields (JSON)", "raw_fields_json"],
];
const font = "Arial";
const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const releases = workbook.worksheets.add("Releases");
summary.showGridLines = false;
releases.showGridLines = false;
summary.tabColor = "#1F4E78";
releases.tabColor = "#5B9BD5";

summary.getRange("A2:F2").format.borders = {
  bottom: { style: "thin", color: "#9EADBA" },
};
summary.getRange("A2").values = [["Catalog collection summary"]];
summary.getRange("A2").format.font = { name: font, size: 14, bold: true, color: "#1F2937" };
summary.getRange("A4:B4").values = [["Metric", "Value"]];
summary.getRange("A5:A13").values = [
  ["Source page"],
  ["Allowed host"],
  ["Release year"],
  ["Exported records"],
  ["Rows with parse errors"],
  ["Candidate tables"],
  ["Eligible catalog tables"],
  ["Rows inspected"],
  ["Rows filtered by year"],
];
summary.getRange("B5:B7").values = [
  [payload.source.final_url],
  [payload.source.allowed_host],
  [payload.collection.release_year],
];
const firstDataRow = 7;
const lastDataRow = firstDataRow + records.length - 1;
summary.getRange("B8").formulas = [[`=COUNTA(Releases!A${firstDataRow}:A${lastDataRow})`]];
summary.getRange("B9").formulas = [[`=COUNTIF(Releases!P${firstDataRow}:P${lastDataRow},"error")`]];
summary.getRange("B10:B13").values = [
  [payload.collection.candidate_tables],
  [payload.collection.eligible_tables],
  [payload.collection.rows_seen],
  [payload.collection.rows_filtered_by_year],
];
summary.getRange("A4:B4").format = {
  fill: "#1F4E78",
  font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
summary.getRange("A5:B13").format.font = { name: font, size: 10, color: "#1F2937" };
summary.getRange("A5:A13").format.fill = "#DCE6F1";
summary.getRange("A4:B13").format.verticalAlignment = "center";
summary.getRange("A4:B13").format.borders = {
  bottom: { style: "thin", color: "#D8DEE6" },
};
summary.getRange("A:A").format.columnWidth = 28;
summary.getRange("B:B").format.columnWidth = 88;
summary.getRange("B5:B6").format.wrapText = false;
summary.getRange("B7").format.numberFormat = "0";
summary.getRange("B8:B13").format.numberFormat = "#,##0";
summary.getRange("A15:B16").values = [
  ["Use", "Review-only collection output. It is not canonical catalog data."],
  ["Safety", "The collector handles one allowlisted host and refuses Fandom/Wikia."],
];
summary.getRange("A15:A16").format.font = { name: font, size: 10, bold: true, color: "#1F2937" };
summary.getRange("B15:B16").format.font = { name: font, size: 10, italic: true, color: "#4B5563" };

releases.getRange("A2:S2").format.borders = {
  bottom: { style: "thin", color: "#9EADBA" },
};
releases.getRange("A2").values = [["Collected release rows"]];
releases.getRange("A2").format.font = { name: font, size: 14, bold: true, color: "#1F2937" };
releases.getRange("A3:B4").values = [
  ["Source URL", payload.source.final_url],
  ["Collected at (UTC)", payload.collection.scraped_at_utc],
];
releases.getRange("A3:A4").format.font = { name: font, size: 10, bold: true, color: "#1F2937" };
releases.getRange("B3:B4").format.font = { name: font, size: 10, color: "#4B5563" };
releases.getRange("A6:S6").values = [columns.map(([label]) => label)];
releases.getRange(`A${firstDataRow}:A${lastDataRow}`).format.numberFormat = "@";
releases.getRange(`B${firstDataRow}:B${lastDataRow}`).format.numberFormat = "0";
releases.getRange(`D${firstDataRow}:E${lastDataRow}`).format.numberFormat = "@";
releases.getRange(`N${firstDataRow}:O${lastDataRow}`).format.numberFormat = "0";
releases.getRange(`R${firstDataRow}:R${lastDataRow}`).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
releases.getRange(`A${firstDataRow}:S${lastDataRow}`).values = records.map((record) =>
  columns.map(([, key]) => record[key] ?? null),
);
releases.getRange("A6:S6").format = {
  fill: "#1F4E78",
  font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
releases.getRange(`A${firstDataRow}:S${lastDataRow}`).format.font = {
  name: font,
  size: 10,
  color: "#1F2937",
};
releases.getRange(`A${firstDataRow}:S${lastDataRow}`).format.verticalAlignment = "center";
releases.getRange(`A${firstDataRow}:S${lastDataRow}`).format.borders = {
  bottom: { style: "thin", color: "#E5E7EB" },
};
releases.getRange(`P${firstDataRow}:P${lastDataRow}`).conditionalFormats.add("containsText", {
  text: "error",
  format: { fill: "#FDE2E2", font: { bold: true, color: "#B91C1C" } },
});
releases.tables.add(`A6:S${lastDataRow}`, true, "CollectedReleases");
releases.freezePanes.freezeRows(6);
releases.freezePanes.freezeColumns(3);
const widths = [
  27, 13, 15, 14, 16, 30, 28, 22, 24, 16, 16, 28, 56, 13, 12, 14, 32, 23, 56,
];
widths.forEach((width, index) => {
  releases.getRangeByIndexes(0, index, lastDataRow, 1).format.columnWidth = width;
});
releases.getRange(`F${firstDataRow}:M${lastDataRow}`).format.wrapText = false;
releases.getRange(`Q${firstDataRow}:S${lastDataRow}`).format.wrapText = false;

workbook.recalculate();
const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:B16",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 4,
});
const releaseCheck = await workbook.inspect({
  kind: "table",
  range: `Releases!A1:S${Math.min(lastDataRow, 12)}`,
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 19,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
for (const sheetName of ["Summary", "Releases"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  if (previewDirectory) {
    await fs.mkdir(previewDirectory, { recursive: true });
    const previewBytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(path.join(previewDirectory, `${sheetName.toLowerCase()}.png`), previewBytes);
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
process.stdout.write(
  JSON.stringify(
    {
      status: "complete",
      output: outputPath,
      records: records.length,
      summary_check: summaryCheck.ndjson,
      release_check: releaseCheck.ndjson,
      formula_errors: errors.ndjson,
    },
    null,
    2,
  ) + "\n",
);
