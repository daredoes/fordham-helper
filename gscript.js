// The contents of this file must be uploaded to a project on script.google.com. 
// When deploying the project, deploy it as a "Web App". It must "execute as ME", and "Anyone" must have access. When you deploy, you will be given a URL that ends in /exec.
// This URL must be placed in `main.py`. The URL it loads DOES NOT WORK.
const SHEET_ID = '1XmZrwbo_X5YDjAfPvk6LoE4YLsWDH00rjzCuK1ZrcmI' // This is the Spreadsheet ID we want to modify

function getSpreadsheet(year='Template') {
  const sheet = SpreadsheetApp.openById(SHEET_ID)
  const activeSheet = sheet.getSheetByName(year)
  if (activeSheet == null) {
    const template = sheet.getSheetByName('Template')
    template.activate()
    const newSheet = sheet.duplicateActiveSheet()
    template.activate()
    newSheet.setName(year)
    return newSheet
  }
  return activeSheet
}

function test() {
  year = '2025'
  getHeaders(year, ['FIDN', 'Coolkids'])
}

function log(event, message){
  SpreadsheetApp.openById(SHEET_ID).getSheetByName('Log').appendRow([new Date(), event, message])
}

function getHeaders(year, headers=[]) {
  const sheet = getSpreadsheet(year)
  const range = sheet.getDataRange()
  const values = range.getValues()

  const HEADERS = {}
  for (let i = 0; i < values[0].length; i++) {
    HEADERS[values[0][i]] = i
  }
  let maxLength = values[0].length
  for (let index in headers) {
    const header = headers[index]
    if (HEADERS[header] === undefined) {
      HEADERS[header] = maxLength
      const cell = sheet.getRange(1, ++maxLength)
      cell.setValue(header)
    }
  }
  Logger.log(HEADERS)
  return HEADERS
}

function updatePersonRow(sheet, person, headers, row) {
  const personKeys = Object.keys(person)
  for (let keyIndex = 0; keyIndex <= personKeys.length; keyIndex++) {
    const COLUMN_INDEX = headers[personKeys[keyIndex]]
    if (COLUMN_INDEX !== undefined) {
      const cell = sheet.getRange(row+1, COLUMN_INDEX+1)
      cell.setValue(person[personKeys[keyIndex]])
    }
  }
}

function createOrUpdatePerson(year, id, person) {
  // 1. Check that a person with the ID does not already exist in our sheet
  // 2a. If they do, update values in the row based on values in the person
  // 2b. Else, add a new row to the sheet putting each value on the person in place by name, not order
  const sheet = getSpreadsheet(year)
  const headers = getHeaders(year)

  const range = sheet.getDataRange()
  const values = range.getValues()

  let found = false;
  const cache = CacheService.getScriptCache()
  const IDS = JSON.parse(cache.get(year + 'IDS') || '{}')
  const NEW_IDS = Object.assign({}, IDS)
  if (Object.keys(IDS).length) {
    const row = IDS[id]
    if (row) {
      updatePersonRow(sheet, person, headers, row)
      found = true
    }
  } else {
    for (let i = 1; i < values.length; i++) {
      const ID_KEY_COLUMN = headers['FIDN']
      const ROW_ID = values[i][ID_KEY_COLUMN]
      NEW_IDS[ROW_ID] = i
      if (ROW_ID === id) {
        updatePersonRow(sheet, person, headers, i)
        found = true
      }
    }
  }
  if (!found) {
    NEW_IDS[id] = values.length
    updatePersonRow(sheet, person, headers, values.length)
  }
  cache.put('IDS', JSON.stringify(NEW_IDS))
  return found
}

// This is the function that ingests the content from the attached python program
function doPost(e) {
  const year = e.parameter.year
  const headers = e.parameter.headers
  Logger.log([year, headers])
  Logger.log(e.postData.contents)
  log('headers', headers)
  log('parameters', e.parameters)
  log('content', e.postData.contents)
  const data = JSON.parse(e.postData.contents)
  // Logger.log(data)
  const idKeys = Object.keys(data)
  getHeaders(year, headers)
  const foundPeople = {}
  for (let idIndex = 0; idIndex < idKeys.length; idIndex++) {
    const id = idKeys[idIndex]
    const person = data[id]
    const wasFound = createOrUpdatePerson(year, id, person)
    foundPeople[id] = wasFound
  }
  return ContentService.createTextOutput(JSON.stringify(foundPeople)).setMimeType(ContentService.MimeType.JSON)
}