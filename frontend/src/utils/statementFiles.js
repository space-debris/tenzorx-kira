export const DEFAULT_SAMPLE_CONTENT =
  'date,description,amount,type\n'
  + '2026-04-01,Supplier Traders,22000,debit\n'
  + '2026-04-02,Customer UPI,48000,credit\n'
  + '2026-04-03,Paytm QR Collection,12600,credit\n'
  + '2026-04-03,Shop Rent,15000,debit\n'
  + '2026-04-04,Grocery Wholesale,18450,debit\n'
  + '2026-04-05,UPI Settlement,22150,credit\n'
  + '2026-04-06,Card Settlement,17300,credit\n'
  + '2026-04-07,Cash Purchase,6200,debit\n';

export const SAMPLE_STATEMENT_FILES = [
  { label: 'Paytm UPI sample PDF', href: '/sample-statements/paytm-dummy-statement.pdf' },
  { label: 'PhonePe UPI sample PDF', href: '/sample-statements/phonepe-dummy-statement.pdf' },
  { label: 'Merchant settlement sample PDF', href: '/sample-statements/paytm-dummy-statement.pdf' },
];

export const XLSX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
export const XLS_MIME_TYPE = 'application/vnd.ms-excel';
export const STATEMENT_FILE_ACCEPT =
  '.csv,.pdf,.xlsx,.xls,text/csv,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel';

export function inferStatementFileType(fileName = '', mimeType = '') {
  const normalizedMime = String(mimeType || '').toLowerCase();
  const normalizedName = String(fileName || '').toLowerCase();

  if (normalizedMime.includes('pdf') || normalizedName.endsWith('.pdf')) {
    return 'application/pdf';
  }
  if (
    normalizedMime.includes('spreadsheetml')
    || normalizedName.endsWith('.xlsx')
  ) {
    return XLSX_MIME_TYPE;
  }
  if (
    normalizedMime.includes('ms-excel')
    || normalizedName.endsWith('.xls')
  ) {
    return XLS_MIME_TYPE;
  }
  return 'text/csv';
}

export function isSpreadsheetStatementType(fileType = '') {
  return [XLSX_MIME_TYPE, XLS_MIME_TYPE].includes(String(fileType || '').toLowerCase());
}

export function isBinaryStatementType(fileType = '') {
  const normalizedType = String(fileType || '').toLowerCase();
  return normalizedType === 'application/pdf' || isSpreadsheetStatementType(normalizedType);
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read file as text'));
    reader.readAsText(file);
  });
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read file as data URL'));
    reader.readAsDataURL(file);
  });
}

export async function readStatementFile(file, detectedType) {
  if (isBinaryStatementType(detectedType)) {
    return readFileAsDataUrl(file);
  }
  return readFileAsText(file);
}

export function summarizeCsvContent(csvText = '') {
  const lines = csvText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const rows = Math.max(0, lines.length - 1);
  let debitRows = 0;
  let creditRows = 0;

  lines.slice(1).forEach((line) => {
    const value = line.toLowerCase();
    if (value.includes(',debit')) debitRows += 1;
    if (value.includes(',credit')) creditRows += 1;
  });

  return { rows, debitRows, creditRows };
}
