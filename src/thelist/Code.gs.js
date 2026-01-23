var BLENDER = {
  'WITH_HEADER': "blended with…",
  'IN_HEADER': "in blends…",
  'RAW': {
    'SHEET_NAME': "blendus synced raw",
    'WITH_COL_INDEX': 0,
    'DATA_START_ROW': 2
  },
  'PRETTY': {
    'SHEET_NAME': "blendus synced pretty",
    'WITH_COL_INDEX': 0,
    'DATA_START_ROW': 3
  },
  'OG': {
    'SHEET_NAME': "blendus og"
  },
  'REGISTRY': {
    'SHEET_NAME': "blends",
    'WITH_COL_NAME': "blendees",
    'DATA_START_ROW': 3
  }
}
var ARTIST = {
  'HEADER_NAME': "aka/artist"
}

function getBlendedWithColumnByName(sheet, headerName) {
  /**
   * Finds the "blended with" column number by its header name (in Row 1).
   * CHECKS THE GLOBAL VARIABLE FIRST TO SEE IF A POSITIVE INTEGER VALUE HAS ALREADY BEEN SET
   * Returns -1 if not found.
   */
  var sheetName = sheet.getName();
  if (sheetName.endsWith("raw")) {
    if (!BLENDER.RAW.WITH_COL_INDEX || BLENDER.RAW.WITH_COL_INDEX < 0) BLENDER.RAW.WITH_COL_INDEX = getColumnIndexByName(sheet, headerName)
    //SpreadsheetApp.getUi().alert("sheet = '"+sheet+"'\nheaderName = '"+headerName+"'\nBLENDER.RAW.WITH_COL_INDEX = "+BLENDER.RAW.WITH_COL_INDEX);
    return BLENDER.RAW.WITH_COL_INDEX
  }
  if (sheetName.endsWith("pretty")) {
    if (!BLENDER.PRETTY.WITH_COL_INDEX || BLENDER.PRETTY.WITH_COL_INDEX < 0) BLENDER.PRETTY.WITH_COL_INDEX = getColumnIndexByName(sheet, headerName)
    //SpreadsheetApp.getUi().alert("sheet = '"+sheet+"'\nheaderName = '"+headerName+"'\nBLENDER.PRETTY.WITH_COL_INDEX = "+BLENDER.PRETTY.WITH_COL_INDEX);
    return BLENDER.PRETTY.WITH_COL_INDEX
  }
}

function getColumnIndexByName(sheet, headerName) {
  var lastCol = sheet.getLastColumn();
  if (lastCol < 1) return -1;
  
  // Grab all headers in Row 1
  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  
  // Find the index of the name (indexOf returns 0-based index, so we add 1)
  var index = headers.indexOf(headerName);

  return index !== -1 ? index + 1 : -1;
}

function onOpen() {
  // --- 1. ONOPEN (Now Auto-Syncs) ---
  SpreadsheetApp.getUi()
    .createMenu('inhumantools')
    .addItem('Refresh Hex Colors', 'colorizeHexColumn')
    .addSeparator() 
    .addItem('Sync & Link "blended with…" (From Raw to Pretty)', 'syncFromRaw') // Manual click = Not silent
    .addItem('Export blend-data (.csv)', 'generateBlendDataExport')
    .addSeparator() 
    .addItem('Find Unpaired Blend Partners', 'findBrokenLinks')
    .addItem('Find Orphaned Artists (Unblended)', 'findOrphanedArtists')
    .addSeparator() // Optional: Adds a line to separate the Export tool
    .addItem('Perform Name/Full Name Maintenance on Blend Registry','maintainBlendRegistry')
    .addItem('Generate Missing xIDENT values for raw Ladies', 'generateMissingIDs')
    // .addItem('Set Up "Blends Registry" (new sheet)', 'setupBlendRegistry')
    .addToUi();

  // Run automatically on load
  // We pass 'true' to enable Silent Mode (no popup alerts)
  syncFromRaw(true);
  colorizeHexColumn();
}

function onChangeTrigger(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  
  // Only run if we are touching the 'blends' registry
  if (sheet.getName() !== BLENDER.REGISTRY.SHEET_NAME) return;

  // Run the sync
  syncRegistryToPeople();
}

function onEdit(e) {
  var cell = e.range;
  var sheet = cell.getSheet();
  var name = sheet.getName();

  // Logic for manual edits 
  if (name === BLENDER.PRETTY.SHEET_NAME) {

    var blendedCol = getBlendedWithColumnByName(sheet, BLENDER.WITH_HEADER); 
    // If column not found, or the edited cell isn't in that column, stop.
    if (blendedCol === -1 || cell.getColumn() !== blendedCol) {
      return;
    }

    // 3. Ignore Header Rows (assuming data starts Row 3)
    if (cell.getRow() < BLENDER.PRETTY.DATA_START_ROW) return;
    
    // Get the value in Column A for this specific row
    var selfValue = sheet.getRange(cell.getRow(), 1).getValue().toString().trim();
    var selectedValue = cell.getValue().toString();
    
    // Check if the selected value contains the self-name
    // We check for "contains" because the selection might be "Tag A, Tag B"
    if (selectedValue.indexOf(selfValue) !== -1 && selfValue !== "") {
      SpreadsheetApp.getUi().alert("⛔ You cannot blend '" + selfValue + "' with herself.");
      cell.setValue(""); // Reject: Clear the cell
      return; // Stop: Don't create links
    }

    // *** RECIPROCAL LINKIFICATION ***
    // We run this BEFORE linkifying the current cell, so both happen smoothly.
    updateReciprocalLinks(cell, selfValue, selectedValue, blendedCol);

    applyLinksToRange(cell);
    highlightChipDuplicates(sheet);

  } else {
    if (name === BLENDER.OG.SHEET_NAME) { // THE ORIGINAL MANUALLY EDITED SHEET, NOW WELL OUT OF DATE
      var column = cell.getColumn();
      // Logger.log(column);
      if (column == 19) {
        // Logger.log('Insta');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://instagram.com/' + e.value)
          .build();
        cell.setRichTextValue(richValue);
      } else if (column == 20) {
        // Logger.log('YouTube');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://youtube.com/@' + e.value)
          .build();
        cell.setRichTextValue(richValue);
      } else if (column == 21) {
        // Logger.log('IMDb');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://imdb.com/name/' + e.value)
          .build();
        cell.setRichTextValue(richValue);
      } else if (column == 22) {
        // Logger.log('listal');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://listal.com/' + e.value)
          .build();
        cell.setRichTextValue(richValue);
      } else if (column == 23) {
        // Logger.log('Wikipedia');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://en.wikipedia.org/wiki/' + e.value)
          .build();
        cell.setRichTextValue(richValue);
      } else if (column == 24) {
        // Logger.log('Bandcamp');
        var richValue = SpreadsheetApp.newRichTextValue()
          .setText(e.value)
          .setLinkUrl('https://' + e.value + '.bandcamp.com/')
          .build();
        cell.setRichTextValue(richValue);
      }
    } else {
      // if (name === BLENDER.REGISTRY.SHEET_NAME) {
      //   syncRegistryToPeople()
      // }

      var hexTest = new RegExp("^[A-F0-9]{6}$").test(e.value);
      // console.info(hexTest);
      if (hexTest) {
        cell.setBackground('#' + e.value);
        return; // STOP! Do not run the rest of the script.
      }
    }
  }
}

function syncFromRaw(silent) {
  var isSilent = (silent === true);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var targetSheet = ss.getSheetByName(BLENDER.PRETTY.SHEET_NAME);
  var sourceSheet = ss.getSheetByName(BLENDER.RAW.SHEET_NAME);
  
  if (!targetSheet || !sourceSheet) {
    if (!isSilent) SpreadsheetApp.getUi().alert("Sheet not found! Check CONFIG names.");
    return;
  }

  // Find Columns
  var rawColBlended = getColumnIndexByName(sourceSheet, BLENDER.WITH_HEADER);
  var rawColInBlends = getColumnIndexByName(sourceSheet, BLENDER.IN_HEADER);
  
  var prettyColBlended = getColumnIndexByName(targetSheet, BLENDER.WITH_HEADER);
  var prettyColInBlends = getColumnIndexByName(targetSheet, BLENDER.IN_HEADER);

  if (rawColBlended == -1 || rawColInBlends == -1 || prettyColBlended == -1 || prettyColInBlends == -1) {
    if (!isSilent) SpreadsheetApp.getUi().alert("Missing required columns in Raw or Pretty sheets.");
    return;
  }

  var lastRowRaw = sourceSheet.getLastRow();
  var totalRows = lastRowRaw - BLENDER.RAW.DATA_START_ROW + 1;
  if (totalRows < 1) return; 

  // Batch Get Data
  var rawValuesBlended = sourceSheet.getRange(BLENDER.RAW.DATA_START_ROW, rawColBlended, totalRows, 1).getValues();
  var rawValuesInBlends = sourceSheet.getRange(BLENDER.RAW.DATA_START_ROW, rawColInBlends, totalRows, 1).getValues();
  
  // A. Write & Link "BLENDED WITH" (Links to Ladies in Pretty Sheet)
  var targetRangeBlended = targetSheet.getRange(BLENDER.PRETTY.DATA_START_ROW, prettyColBlended, totalRows, 1);
  targetRangeBlended.setBackground(null);
  targetRangeBlended.setValues(rawValuesBlended);
  applyLinksToRange(targetRangeBlended, "LADIES"); 

  // B. Write & Link "IN BLENDS" (Links to Hexcodes in Registry Sheet)
  var targetRangeInBlends = targetSheet.getRange(BLENDER.PRETTY.DATA_START_ROW, prettyColInBlends, totalRows, 1);
  targetRangeInBlends.setBackground(null);
  
  // *** SAFEGUARD: FORCE PLAIN TEXT FOR HEXCODES ***
  targetRangeInBlends.setNumberFormat('@'); 
  
  targetRangeInBlends.setValues(rawValuesInBlends);
  applyLinksToRange(targetRangeInBlends, "BLENDS");

  // Optional: Highlight invalid names
  if (typeof highlightChipDuplicates === 'function') {
    highlightChipDuplicates(targetSheet);
  }

  if (!isSilent) {
    SpreadsheetApp.getUi().alert("Synced " + totalRows + " rows from Raw Sheet.");
  }
}

/**
 * 2. HELPER: APPLY LINKS
 * type="LADIES" -> Links to NAME column in PRETTY sheet.
 * type="BLENDS" -> Links to HEXCODE column in REGISTRY sheet.
 */
function applyLinksToRange(range, type) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var values = range.getValues();
  
  var lookupSheet, lookupValues, lookupId, lookupStartRow;

  if (type === "LADIES") {
    // Target: Pretty Sheet (Names)
    lookupSheet = ss.getSheetByName(BLENDER.PRETTY.SHEET_NAME);
    lookupStartRow = BLENDER.PRETTY.DATA_START_ROW;
    
    if (!lookupSheet) return; 

    // Find "NAME" column in Pretty Sheet
    var nameColIdx = getColumnIndexByName(lookupSheet, "NAME");
    var lastRow = lookupSheet.getLastRow();
    
    if (lastRow < lookupStartRow) {
      lookupValues = [];
    } else {
      lookupValues = lookupSheet.getRange(lookupStartRow, nameColIdx, lastRow - lookupStartRow + 1, 1)
        .getValues().flat().map(function(s) { return s.toString().trim(); });
    }
      
  } else if (type === "BLENDS") {
    // Target: Registry Sheet (Hexcodes)
    lookupSheet = ss.getSheetByName(BLENDER.REGISTRY.SHEET_NAME);
    lookupStartRow = BLENDER.REGISTRY.DATA_START_ROW;
    
    if (!lookupSheet) return;
    
    // Find "Hexcode" column in Registry Sheet
    var headers = lookupSheet.getRange(1, 1, 1, lookupSheet.getLastColumn()).getValues()[0];
    var hexColIdx = headers.indexOf("Hexcode");
    if (hexColIdx == -1) hexColIdx = 0; // Fallback to Col A (Index 0) -> +1 for getRange
    
    var lastRow = lookupSheet.getLastRow();
    if (lastRow < lookupStartRow) {
      lookupValues = [];
    } else {
      // +1 because getRange is 1-based, indexOf is 0-based
      lookupValues = lookupSheet.getRange(lookupStartRow, hexColIdx + 1, lastRow - lookupStartRow + 1, 1)
        .getValues().flat().map(function(s) { return s.toString().trim(); });
    }
  }

  lookupId = lookupSheet.getSheetId();
  var richTextOutput = [];

  for (var i = 0; i < values.length; i++) {
    var cellValue = values[i][0];
    
    if (cellValue === null || cellValue === "" || cellValue === undefined) {
      richTextOutput.push([SpreadsheetApp.newRichTextValue().setText("").build()]);
      continue;
    }

    var tags = cellValue.toString().split(",").map(function(s) { return s.trim(); });
    var builder = SpreadsheetApp.newRichTextValue();
    var currentText = "";
    var linkMap = []; 

    tags.forEach(function(tag, index) {
      if (index > 0) currentText += ", ";
      
      var startIndex = currentText.length;
      currentText += tag;
      var endIndex = currentText.length;
      
      var sourceIndex = lookupValues.indexOf(tag);
      if (sourceIndex !== -1) {
        var rowNum = sourceIndex + lookupStartRow; 
        var url = "#gid=" + lookupId + "&range=A" + rowNum;
        linkMap.push({ start: startIndex, end: endIndex, url: url });
      }
    });

    builder.setText(currentText);
    linkMap.forEach(function(link) {
      builder.setLinkUrl(link.start, link.end, link.url);
    });

    richTextOutput.push([builder.build()]);
  }

  range.setRichTextValues(richTextOutput);
}

function updateReciprocalLinks(sourceRange, sourceName, targetNamesString, targetColIndex) {
  /**
   * RECIPROCAL LINKING LOGIC
   * If Row A selects Row B, this function goes to Row B and selects Row A.
   */
  var sheet = sourceRange.getSheet();
  var lastRow = sheet.getLastRow();
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  
  // 1. Get the list of all names, map names -> row numbers
  var allNames = sheet.getRange(BLENDER.PRETTY.DATA_START_ROW, NAME_COL_INDEX, lastRow - BLENDER.PRETTY.DATA_START_ROW + 1, 1).getValues().flat().map(String);
  
  // 2. Parse the target names (the ones just selected)
  if (!targetNamesString) return;
  var targets = targetNamesString.split(",").map(function(s) { return s.trim(); });
  
  // 3. Loop through each person we just selected
  targets.forEach(function(targetName) {
    if (targetName === "") return;
    
    // Find the row number for this target person
    var targetIndex = allNames.indexOf(targetName);
    
    if (targetIndex !== -1) {
      var targetRowNum = targetIndex + BLENDER.PRETTY.DATA_START_ROW; // +3 because data starts at A3
      
      // Don't update if it's the same row (sanity check)
      if (targetRowNum === sourceRange.getRow()) return;
      
      var targetCell = sheet.getRange(targetRowNum, targetColIndex); // Col Y
      var currentTargetValue = targetCell.getValue().toString();
      
      // 4. Check if the SOURCE name is already in the TARGET's list
      //    We split and check strictly to avoid partial matches (e.g. "Dan" matching "Danny")
      var currentList = currentTargetValue.split(",").map(function(s) { return s.trim(); }).filter(String);
      
      if (currentList.indexOf(sourceName) === -1) {
        // It's missing! Add it.
        currentList.push(sourceName);
        
        // Join it back together
        var newValue = currentList.join(", ");
        
        // Update the cell
        targetCell.setValue(newValue);
        
        // 5. IMPORTANT: Linkify the target cell immediately
        //    (so it doesn't wait for a human click to turn blue)
        applyLinksToRange(targetCell);
        
        // Optional: Remove validation on target so it looks clean immediately
        // targetCell.clearDataValidations();
      }
    }
  });
}

function highlightChipDuplicates(sheet) {
  /**
   * CHIP-ONLY DUPLICATE HIGHLIGHTER
   * Only runs on complex columns where native Conditional Formatting fails.
   */
  var DUPE_FINDER = [
    { 
      colIndex: getColumnIndexByName(sheet, ARTIST.HEADER_NAME),       // Column E (The Chip Column)
      color: "#bfdfcc"  
    }
    // If you ever have another CHIP column, add it here:
    // { colIndex: 8, color: "#FFF2CC" }
  ];
  
  var lastRow = sheet.getLastRow();
  if (lastRow < BLENDER.PRETTY.DATA_START_ROW) return;

  DUPE_FINDER.forEach(function(rule) {
    var colIndex = rule.colIndex;
    var highlightColor = rule.color;
    
    var range = sheet.getRange(BLENDER.PRETTY.DATA_START_ROW, colIndex, lastRow - BLENDER.PRETTY.DATA_START_ROW + 1, 1);
    var values = range.getValues();
    
    // 1. Build Frequency Map
    var chipCounts = {};

    for (var i = 0; i < values.length; i++) {
      var cellVal = values[i][0].toString();
      if (cellVal === "") continue;

      // Split by comma to count individual chips
      var chips = cellVal.split(",").map(function(s) { return s.trim(); });

      chips.forEach(function(chip) {
        if (chip === "") return;
        var cleanChip = chip; // Add .toLowerCase() here if you want case-insensitive
        
        if (!chipCounts[cleanChip]) {
          chipCounts[cleanChip] = 0;
        }
        chipCounts[cleanChip]++;
      });
    }

    // 2. Apply Colors
    var newBackgrounds = [];

    for (var i = 0; i < values.length; i++) {
      var cellVal = values[i][0].toString();
      var isDupe = false;

      if (cellVal !== "") {
        var chips = cellVal.split(",").map(function(s) { return s.trim(); });
        
        for (var j = 0; j < chips.length; j++) {
          if (chipCounts[chips[j]] > 1) {
            isDupe = true;
            break; 
          }
        }
      }
      newBackgrounds.push([ isDupe ? highlightColor : null ]);
    }

    range.setBackgrounds(newBackgrounds);
  });
}

function syncRegistryToPeople() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const rawSheet = ss.getSheetByName(BLENDER.RAW.SHEET_NAME);  
  const regSheet = ss.getSheetByName(BLENDER.REGISTRY.SHEET_NAME);

  if (!regSheet || !rawSheet) {
    console.error("Sync Error: Missing sheets.");
    return;
  }  

  // --- 1. DYNAMICALLY FIND COLUMN INDEXES ---
  const regHeaders = regSheet.getRange(1, 1, 1, regSheet.getLastColumn()).getValues()[0];
  const rawHeaders = rawSheet.getRange(1, 1, 1, rawSheet.getLastColumn()).getValues()[0];

  const regBlendColIdx = regHeaders.indexOf(BLENDER.REGISTRY.WITH_COL_NAME); 
  let regHexColIdx = regHeaders.indexOf("Hexcode"); 
  if (regHexColIdx === -1) regHexColIdx = 0; 

  const rawNameColIdx = rawHeaders.indexOf("NAME");
  const rawPartnersColIdx = rawHeaders.indexOf(BLENDER.WITH_HEADER); 
  const rawHexcodesColIdx = rawHeaders.indexOf(BLENDER.IN_HEADER);   

  const missing = [];
  if (regBlendColIdx === -1) missing.push(`'${BLENDER.REGISTRY.WITH_COL_NAME}' in Registry`);
  if (rawNameColIdx === -1) missing.push(`'NAME' in Raw`);
  if (rawPartnersColIdx === -1) missing.push(`'${BLENDER.WITH_HEADER}' in Raw`);
  if (rawHexcodesColIdx === -1) missing.push(`'${BLENDER.IN_HEADER}' in Raw`);

  if (missing.length > 0) {
    SpreadsheetApp.getUi().alert(`Error: Could not find headers: ${missing.join(", ")}`);
    return;
  }

  // --- 2. READ REGISTRY ---
  const lastRegRow = regSheet.getLastRow();
  if (lastRegRow < BLENDER.REGISTRY.DATA_START_ROW) return;

  const regData = regSheet.getRange(BLENDER.REGISTRY.DATA_START_ROW, 1, lastRegRow - BLENDER.REGISTRY.DATA_START_ROW + 1, regSheet.getLastColumn()).getValues();
  
  const connections = {};      
  const blendInclusions = {};  
  const cleanBlendColumn = []; 

  regData.forEach(row => {
    let blendString = row[regBlendColIdx]; 
    let hexcode = row[regHexColIdx];
    let sortedString = "";

    if (blendString) {
      const participants = blendString.toString().split(",").map(p => p.trim()).filter(p => p);
      participants.sort(); 
      sortedString = participants.join(", ");

      participants.forEach(person => {
        if (!connections[person]) connections[person] = new Set();
        if (!blendInclusions[person]) blendInclusions[person] = new Set();
        
        // Ensure hexcode is string
        if (hexcode) blendInclusions[person].add(hexcode.toString().trim());

        participants.forEach(partner => {
          if (person !== partner) connections[person].add(partner);
        });
      });
    }
    cleanBlendColumn.push([sortedString]);
  });

  // --- 3. UPDATE REGISTRY ---
  var regTargetRange = regSheet.getRange(BLENDER.REGISTRY.DATA_START_ROW, regBlendColIdx + 1, cleanBlendColumn.length, 1);
  regTargetRange.setValues(cleanBlendColumn);
  applyLinksToRange(regTargetRange, "LADIES"); 
  
  console.log("Registry 'blendees' column sorted and linked.");

  // --- 4. UPDATE RAW PEOPLE SHEET ---
  const lastRawRow = rawSheet.getLastRow();
  const peopleData = rawSheet.getRange(BLENDER.RAW.DATA_START_ROW, 1, lastRawRow - BLENDER.RAW.DATA_START_ROW + 1, rawSheet.getLastColumn()).getValues();
  
  const outputPartners = []; 
  const outputHexcodes = []; 

  peopleData.forEach(row => {
    const name = row[rawNameColIdx].toString().trim(); 
    
    // A. Partners
    if (connections[name]) {
      outputPartners.push([Array.from(connections[name]).sort().join(", ")]);
    } else {
      outputPartners.push([""]); 
    }

    // B. Hexcodes
    if (blendInclusions[name]) {
      outputHexcodes.push([Array.from(blendInclusions[name]).sort().join(", ")]);
    } else {
      outputHexcodes.push([""]);
    }
  });

  // Write Partners
  rawSheet.getRange(BLENDER.RAW.DATA_START_ROW, rawPartnersColIdx + 1, outputPartners.length, 1).setValues(outputPartners);
  
  // Write Hexcodes (WITH PLAIN TEXT SAFEGUARD)
  var rawHexRange = rawSheet.getRange(BLENDER.RAW.DATA_START_ROW, rawHexcodesColIdx + 1, outputHexcodes.length, 1);
  
  // *** SAFEGUARD: FORCE PLAIN TEXT FOR HEXCODES ***
  rawHexRange.setNumberFormat('@');
  
  rawHexRange.setValues(outputHexcodes);
  
  if (typeof generateMissingIDs === 'function') generateMissingIDs();
  console.log("Registry Sync Complete.");
}

function colorizeHexColumn() {
  /**
   * Scans Column A of the 'blends' sheet.
   * Sets background to the hex code value.
   * Sets text color to Black or White based on contrast.
   */
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(BLENDER.REGISTRY.SHEET_NAME);
  if (!sheet) return;
  const HEX_COL_INDEX = getColumnIndexByName(sheet, "hexcode"); // Column A
  const START_ROW = BLENDER.REGISTRY.DATA_START_ROW;     // Skip header

  const lastRow = sheet.getLastRow();
  if (lastRow < START_ROW) return;

  // Get all hex codes in one batch for speed
  const range = sheet.getRange(START_ROW, HEX_COL_INDEX, lastRow - START_ROW + 1, 1);
  const values = range.getValues();
  
  const backgrounds = [];
  const fontColors = [];

  for (let i = 0; i < values.length; i++) {
    let hex = values[i][0].toString().trim();
    
    // Check if it looks like a valid 6-digit hex code (A1B2C3)
    // We allow it with or without the '#' prefix
    const cleanHex = hex.replace('#', '');
    
    if (/^[0-9A-Fa-f]{6}$/.test(cleanHex)) {
      // 1. Set Background (needs # prefix)
      backgrounds.push([`#${cleanHex}`]);
      
      // 2. Calculate Contrast (YIQ Formula)
      // Extract RGB values
      const r = parseInt(cleanHex.substr(0, 2), 16);
      const g = parseInt(cleanHex.substr(2, 2), 16);
      const b = parseInt(cleanHex.substr(4, 2), 16);
      
      // Calculate luminance (perceived brightness)
      const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
      
      // Threshold: 128 is the standard halfway point
      // If bright (>=128), text is black. If dark (<128), text is white.
      fontColors.push([yiq >= 128 ? 'black' : 'white']);
      
    } else {
      // If invalid/empty, reset to white background/black text
      backgrounds.push([null]); 
      fontColors.push(['black']);
    }
  }

  // Apply changes in one batch (much faster than loop)
  range.setBackgrounds(backgrounds);
  range.setFontColors(fontColors);
}

function findBrokenLinks() {
  /**
   * AUDIT FUNCTION
   * Scans Column 'Blended With'.
   * If Row A links to Row B, checks if Row B links back to Row A.
   * Highlights broken links in RED.
   */
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(BLENDER.PRETTY.SHEET_NAME);
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var lastRow = sheet.getLastRow();
  
  var blendedCol = getBlendedWithColumnByName(sheet, BLENDER.WITH_HEADER);
  if (blendedCol === -1) {
    SpreadsheetApp.getUi().alert("Column not found.");
    return;
  }

  // 1. Get Normalized Data
  var nameValues = sheet.getRange(BLENDER.PRETTY.DATA_START_ROW, NAME_COL_INDEX, lastRow - BLENDER.PRETTY.DATA_START_ROW + 1, 1).getValues().flat().map(function(s) { return s.toString().normalize("NFC"); });

  var linkRange = sheet.getRange(BLENDER.PRETTY.DATA_START_ROW, blendedCol, lastRow - BLENDER.PRETTY.DATA_START_ROW + 1, 1);
  var linkValues = linkRange.getValues().flat().map(String);
  
  var backgrounds = [];
  var errorLog = []; // NEW: Store specific error messages

  linkRange.setBackground(null);

  for (var i = 0; i < nameValues.length; i++) {
    var sourceName = nameValues[i];
    var targetsString = linkValues[i];
    var isRowBroken = false;

    if (targetsString === "") {
      backgrounds.push([null]);
      continue;
    }

    var targets = targetsString.split(",").map(function(s) { return s.trim().normalize("NFC"); });

    for (var j = 0; j < targets.length; j++) {
      var targetName = targets[j];
      if (targetName === "") continue;

      var targetIndex = nameValues.indexOf(targetName);
      
      if (targetIndex === -1) {
        // ERROR 1: Name doesn't exist
        isRowBroken = true;
        errorLog.push("❌ '" + sourceName + "' links to non-existent '" + targetName + "'");
      } else {
        var targetLinks = linkValues[targetIndex];
        var targetList = targetLinks.split(",").map(function(s) { return s.trim().normalize("NFC"); });
        
        if (targetList.indexOf(sourceName) === -1) {
          // ERROR 2: One-way link
          isRowBroken = true;
          // Only log the first few to avoid spamming
          if (errorLog.length < 20) {
            errorLog.push("⚠️ '" + sourceName + "' links to '" + targetName + "', but '" + targetName + "' does not link back.");
          }
        }
      }
    }

    if (isRowBroken) {
      backgrounds.push(["#FFCCCC"]); 
    } else {
      backgrounds.push([null]);
    }
  }

  linkRange.setBackgrounds(backgrounds);
  
  // Show the detailed report
  if (errorLog.length > 0) {
    var msg = "Found " + errorLog.length + " issues. First 10:\n\n" + errorLog.slice(0, 10).join("\n");
    SpreadsheetApp.getUi().alert(msg);
  } else {
    SpreadsheetApp.getUi().alert("✅ All links are reciprocal and valid!");
  }
}

function findOrphanedArtists() {
  /**
   * AUDIT: FIND ORPHANED ARTISTS
   * Scans the sheet for rows that have an Artist (Col E) 
   * but NO Blended connections (Target Col).
   * useful for finding folders/pairs you skipped during manual entry.
   */
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(BLENDER.PRETTY.SHEET_NAME);
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var ARTIST_COL_INDEX = getColumnIndexByName(sheet, ARTIST.HEADER_NAME);  
  var BLEND_COL_INDEX = getBlendedWithColumnByName(sheet, BLENDER.WITH_HEADER); 

  var START_ROW = BLENDER.PRETTY.DATA_START_ROW;
  // --------------

  var lastRow = sheet.getLastRow();
  var range = sheet.getRange(START_ROW, 1, lastRow - START_ROW + 1, Math.max(ARTIST_COL_INDEX, BLEND_COL_INDEX));
  var values = range.getValues();
  
  var orphans = [];

  for (var i = 0; i < values.length; i++) {
    var rowData = values[i];
    
    // Arrays are 0-indexed, so Column A is index 0.
    // We need to subtract 1 from the CONFIG indices.
    var name = rowData[NAME_COL_INDEX - 1];
    var artist = rowData[ARTIST_COL_INDEX - 1];
    var blendData = rowData[BLEND_COL_INDEX - 1];

    // LOGIC:
    // 1. Must have a Name.
    // 2. Must have an Artist (indicating it's a real entry, not a spacer).
    // 3. Blend Column must be EMPTY (indicated skipped entry).
    if (name && artist && (!blendData || blendData.toString().trim() === "")) {
      orphans.push("Row " + (i + START_ROW) + ": " + name + " (" + artist + ")");
    }
  }

  // Report Results
  if (orphans.length > 0) {
    var htmlOutput = HtmlService.createHtmlOutput(
      "<style>body { font-family: sans-serif; }</style>" +
      "<h3>Found " + orphans.length + " Orphaned Artists</h3>" +
      "<p>These rows have an Artist listed but no Blend connections:</p>" +
      "<ul><li>" + orphans.join("</li><li>") + "</li></ul>"
    ).setWidth(400).setHeight(600);
    
    SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'Orphan Report');
  } else {
    SpreadsheetApp.getUi().alert('Good news! Every row with an Artist has at least one Blend connection.');
  }
}

function createHashID(name, salt) {
  /**
   * HELPER: Computes 'x' + 5-char Hex Hash from a string.
   * Matches Python's hashlib.md5(name.lower()).hexdigest()[:5].upper()
   */
  // Normalize: lowercase, trim. Append salt if > 0.
  // Logic: "miley cyrus" or "miley cyrus_1"
  let input = name.toLowerCase();
  if (salt > 0) {
    input += "_" + salt;
  }
  
  // Compute MD5 Digest (Returns signed byte array)
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, input);
  
  // Convert Bytes to Hex String
  let hexString = "";
  for (let j = 0; j < digest.length; j++) {
    let byteVal = digest[j];
    if (byteVal < 0) byteVal += 256; // Handle Java's signed bytes
    let byteHex = byteVal.toString(16);
    if (byteHex.length === 1) byteHex = "0" + byteHex; // Pad single digits
    hexString += byteHex;
  }
  
  // Format: x + first 5 chars + Uppercase
  return "x" + hexString.substring(0, 5).toUpperCase();
}

function generateMissingIDs() {
  /**
   * Generates unique IDs for the "blendus synced raw" sheet.
   * Format: 'x' + 5 Hex Digits (e.g. xA1B2C)
   * Source: Column B (Name)
   * Target: Column A (ID)
   */
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(BLENDER.RAW.SHEET_NAME);
  
  if (!sheet) {
    console.error("Sheet not found: " + BLENDER.RAW.SHEET_NAME);
    return;
  }
  
  // 1. CONFIGURATION
  // Assuming headers are in Row 1. Data starts Row 2.
  const ID_COL_INDEX = getColumnIndexByName(sheet, "xIDENT"); 
  // const NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return; // No data
  
  // Read Col A (IDs) and Col B (Names) in one batch
  const range = sheet.getRange(BLENDER.RAW.DATA_START_ROW, ID_COL_INDEX, lastRow - BLENDER.RAW.DATA_START_ROW + 1, 2);
  const data = range.getValues();
  
  // 2. MAP EXISTING IDs
  // We need to know which IDs are already taken to avoid collisions
  const usedIDs = new Set();
  data.forEach(row => {
    const id = row[0].toString().trim();
    if (id !== "") {
      usedIDs.add(id);
    }
  });
  
  const updates = []; // Will hold the new values for Column A
  let newCount = 0;
  
  // 3. GENERATE MISSING IDs
  for (let i = 0; i < data.length; i++) {
    const currentID = data[i][0].toString().trim();
    const name = data[i][1].toString().trim();
    
    // Case 1: ID already exists -> Keep it
    if (currentID !== "") {
      updates.push([currentID]);
      continue;
    }
    
    // Case 2: Name is empty -> No ID
    if (name === "") {
      updates.push([""]);
      continue;
    }
    
    // Case 3: Mint a new ID
    let salt = 0;
    let candidateID = createHashID(name, salt);
    
    // Collision Loop: If ID taken, increment salt and re-hash
    while (usedIDs.has(candidateID)) {
      salt++;
      candidateID = createHashID(name, salt);
    }
    
    usedIDs.add(candidateID); // Mark as used for future rows
    updates.push([candidateID]);
    newCount++;
  }
  
  // 4. WRITE BACK
  // We overwrite Column A with the updated list (preserving existing, filling new)
  if (newCount > 0) {
    sheet.getRange(BLENDER.RAW.DATA_START_ROW, ID_COL_INDEX, updates.length, 1).setValues(updates);
    console.log(`Minted ${newCount} new IDs.`);
    SpreadsheetApp.getUi().alert(`Minted ${newCount} new IDs.`);
  } else {
    console.log("No missing IDs found.");
  }
}

function generateBlendDataExport() {
  /**
   * EXPORT BLEND DATA
   * Creates a new sheet named "blend-data" with a simple Source,Target list.
   * Run this, then File > Download > CSV on the new sheet.
   */
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(BLENDER.PRETTY.SHEET_NAME);
  
  // --- CONFIG ---
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var BLEND_COL_INDEX = getBlendedWithColumnByName(sheet, BLENDER.WITH_HEADER); 
  var START_ROW = BLENDER.PRETTY.DATA_START_ROW;
  // --------------

  var lastRow = sheet.getLastRow();
  var data = sheet.getRange(START_ROW, 1, lastRow - START_ROW + 1, Math.max(NAME_COL_INDEX, BLEND_COL_INDEX)).getValues();
  
  var exportRows = [["Source", "Target", "Type"]]; // Header for Gephi
  var seenPairs = new Set();

  for (var i = 0; i < data.length; i++) {
    var source = data[i][NAME_COL_INDEX - 1].toString().trim();
    var targetsRaw = data[i][BLEND_COL_INDEX - 1].toString();

    if (source && targetsRaw) {
      var targets = targetsRaw.split(",");
      
      targets.forEach(function(target) {
        var t = target.trim();
        if (t !== "") {
          // Create a unique key (A|B) sorting them ensures A->B and B->A are treated as one link
          var pairKey = [source, t].sort().join("|");
          
          // Only add if we haven't seen this connection yet
          if (!seenPairs.has(pairKey)) {
            exportRows.push([source, t, "Undirected"]);
            seenPairs.add(pairKey);
          }
        }
      });
    }
  }

  // Create or Overwrite the Export Sheet
  var exportSheetName = "blend-data";
  var exportSheet = ss.getSheetByName(exportSheetName);
  if (exportSheet) {
    exportSheet.clear();
  } else {
    exportSheet = ss.insertSheet(exportSheetName);
  }

  // Paste Data
  exportSheet.getRange(1, 1, exportRows.length, 3).setValues(exportRows);
  
  SpreadsheetApp.getUi().alert("Export Ready! Go to the 'blend-data' sheet tab and select File > Download > Comma Separated Values (.csv).");
}

/**
 * MAINTENANCE: Enforce Canonical Names in Registry
 * * Updated to handle COMMA-SEPARATED LISTS of names in a single cell.
 */
function maintainBlendRegistry() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  let logOutput = []; 
  
  // --- CONFIGURATION ---
  const RAW_SHEET_NAME = BLENDER.RAW.SHEET_NAME;
  const REGISTRY_SHEET_NAME = BLENDER.REGISTRY.SHEET_NAME; 
  const TARGET_HEADERS = [BLENDER.REGISTRY.WITH_COL_NAME]; 
  // ---------------------

  function normalizeKey(str) {
    if (!str) return "";
    return String(str)
      .normalize('NFC')
      .replace(/\u00A0/g, ' ')
      .trim()
      .toLowerCase();
  }

  const rawSheet = ss.getSheetByName(RAW_SHEET_NAME);
  const regSheet = ss.getSheetByName(REGISTRY_SHEET_NAME);

  if (!rawSheet || !regSheet) {
    ui.alert("ERROR: Missing sheet(s).");
    return;
  }

  // 1. MAP BUILDER
  const rawHeaders = rawSheet.getRange(1, 1, 1, rawSheet.getLastColumn()).getValues()[0];
  const colNameIndex = rawHeaders.findIndex(h => normalizeKey(h) === "name");
  const colFullIndex = rawHeaders.findIndex(h => normalizeKey(h) === "full name");
  const colXIDIndex  = rawHeaders.findIndex(h => normalizeKey(h) === "xident");

  if (colNameIndex === -1) {
    ui.alert("CRITICAL ERROR: Could not find 'NAME' column.");
    return;
  }

  const lastRawRow = rawSheet.getLastRow();
  const rawData = rawSheet.getRange(2, 1, lastRawRow - 1, rawSheet.getLastColumn()).getValues();
  let nameMap = {};

  rawData.forEach(row => {
    let officialName = row[colNameIndex];
    if (officialName) {
      let officialKey = normalizeKey(officialName);
      nameMap[officialKey] = officialName; 

      if (colFullIndex > -1 && row[colFullIndex]) {
        let fullKey = normalizeKey(row[colFullIndex]);
        if (fullKey) nameMap[fullKey] = officialName;
      }
      if (colXIDIndex > -1 && row[colXIDIndex]) {
        let xKey = normalizeKey(row[colXIDIndex]);
        if (xKey) nameMap[xKey] = officialName;
      }
    }
  });

  logOutput.push(`Map built. Keys: ${Object.keys(nameMap).length}.`);

  // 2. SCAN & SPLIT
  const regHeaders = regSheet.getRange(1, 1, 1, regSheet.getLastColumn()).getValues()[0];
  const lastRegRow = regSheet.getLastRow();
  
  if (lastRegRow < 2) {
    ui.alert("Registry is empty.");
    return;
  }

  TARGET_HEADERS.forEach(target => {
    let colIndex = regHeaders.findIndex(h => normalizeKey(h) === normalizeKey(target));
    
    if (colIndex > -1) {
      logOutput.push(`Scanning Column: "${regHeaders[colIndex]}"...`);
      
      let range = regSheet.getRange(2, colIndex + 1, lastRegRow - 1, 1);
      let values = range.getValues();
      let changes = 0;

      for (let i = 0; i < values.length; i++) {
        let currentVal = String(values[i][0]);
        
        if (currentVal && currentVal.trim() !== "") {
          
          // SPLIT by comma (handling spaces around commas)
          let names = currentVal.split(",");
          let correctedNames = [];
          let hasRowChange = false;

          names.forEach(name => {
            let originalPart = name.trim(); // Keep original spacing just in case
            let lookup = normalizeKey(name);
            
            if (nameMap[lookup]) {
              // We found a match in the map
              correctedNames.push(nameMap[lookup]);
              
              // Did we actually change anything?
              if (nameMap[lookup] !== originalPart) {
                hasRowChange = true;
              }
            } else {
              // No match found, keep original text
              correctedNames.push(originalPart);
            }
          });

          // If any name in the list was updated, write back the whole list
          if (hasRowChange) {
            // Join back with standard ", " separator
            values[i][0] = correctedNames.join(", ");
            changes++;
          }
        }
      }

      if (changes > 0) {
        range.setValues(values);
        logOutput.push(`SUCCESS: Updated ${changes} rows in "${target}".`);
      } else {
        logOutput.push(`No changes needed for "${target}".`);
      }

    } else {
      logOutput.push(`WARNING: Column "${target}" not found.`);
    }
  });

  ui.alert("Maintenance Report", logOutput.join("\n"), ui.ButtonSet.OK);
}

function setupBlendRegistry() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // --- CONFIGURATION ---
  const SOURCE_SHEET_NAME = ss.getSheetByName(BLENDER.RAW.SHEET_NAME);
  const TARGET_SHEET_NAME = BLENDER.REGISTRY.SHEET_NAME;
  
  // COLUMN INDICES (0-based)
  const COL_NAME = 0;       // Column A: Name
  const COL_OCCUPATION = getColumnIndexByName(SOURCE_SHEET_NAME, "whaddayado"); // Column E: Occupation
  const COL_BLENDS = getBlendedWithColumnByName(SOURCE_SHEET_NAME, BLENDER.WITH_HEADER) - 1;  // Column X: The comma-separated list of partners
  
  // Keywords
  const MUSIC_KEYWORDS = ["singer", "musician", "songwriter", "rapper", "vocalist", "band", "music"];
  const ACTING_KEYWORDS = ["actress", "actor", "hollywood", "film", "tv", "star"];

  // 1. GET DATA
  const sourceSheet = ss.getSheetByName(SOURCE_SHEET_NAME);
  if (!sourceSheet) {
    SpreadsheetApp.getUi().alert(`Error: Could not find sheet '${SOURCE_SHEET_NAME}'.`);
    return;
  }
  
  const lastRow = sourceSheet.getLastRow();
  // Fetch all data at once for speed
  const data = sourceSheet.getRange(BLENDER.RAW.DATA_START_ROW, 1, lastRow - BLENDER.RAW.DATA_START_ROW + 1, sourceSheet.getLastColumn()).getValues();
  
  // 2. BUILD OCCUPATION MAP
  // We need to know everyone's job before we can categorize their relationships
  const occupationMap = new Map();
  
  data.forEach(row => {
    const name = row[COL_NAME];
    // Convert to string, lower case, handle blanks
    const job = (row[COL_OCCUPATION] || "").toString().toLowerCase(); 
    if (name) {
      occupationMap.set(name.toString().trim(), job);
    }
  });

  // 3. EXTRACT AND DEDUPLICATE BLENDS
  const uniqueBlends = new Set();
  const processedRows = []; // Will hold the final array for the sheet

  data.forEach(row => {
    const personA = (row[COL_NAME] || "").toString().trim();
    const connectionsString = (row[COL_BLENDS] || "").toString();

    if (!personA || !connectionsString) return;

    // Split Col W by comma to find partners
    const partners = connectionsString.split(",");

    partners.forEach(p => {
      const personB = p.trim();
      if (!personB) return;

      // DEDUPLICATION TRICK:
      // Sort the names alphabetically so "Miley, Dua" and "Dua, Miley" 
      // both generate the same key: "Dua Lipa|Miley Cyrus"
      const pair = [personA, personB].sort();
      const uniqueKey = pair.join("|");

      // Only proceed if we haven't seen this pair yet
      if (!uniqueBlends.has(uniqueKey)) {
        uniqueBlends.add(uniqueKey);

        // --- CLASSIFY THE GROUP ---
        const jobA = occupationMap.get(personA) || "";
        const jobB = occupationMap.get(personB) || "";
        
        let group = "Composite Portraits"; // Default

        const isMusician = (job) => MUSIC_KEYWORDS.some(k => job.includes(k));
        const isActor = (job) => ACTING_KEYWORDS.some(k => job.includes(k));

        // Logic: Both must match the category
        if (isMusician(jobA) && isMusician(jobB)) {
          group = "Crossbred Songbirds";
        } else if (isActor(jobA) && isActor(jobB)) {
          group = "Folie à Deux";
        }

        // Format for the sheet: "Person A, Person B"
        const blendees = `${pair[0]}, ${pair[1]}`;

        // Add to our list
        // [hexcode, blendees, blend_type, date, MJv, best, group, Quiz Hint]
        processedRows.push(["", blendees, "", "", "", "", group, ""]);
      }
    });
  });

  // 4. WRITE TO TARGET SHEET
  let targetSheet = ss.getSheetByName(TARGET_SHEET_NAME);
  if (!targetSheet) {
    targetSheet = ss.insertSheet(TARGET_SHEET_NAME);
  }
  
  // Headers
  if (targetSheet.getLastRow() === 0) {
    const headers = [["hexcode", "blendees", "blend_type", "date", "MJv", "best", "group", "Quiz Hint"]];
    targetSheet.getRange(1, 1, 1, headers[0].length).setValues(headers).setFontWeight("bold");
    targetSheet.setFrozenRows(1);
  }

  // Append Data
  if (processedRows.length > 0) {
    const startRow = targetSheet.getLastRow() + 1;
    targetSheet.getRange(startRow, 1, processedRows.length, processedRows[0].length).setValues(processedRows);
  }

  // 5. DATA VALIDATION & FORMATTING
  const fullRangeRow = targetSheet.getLastRow();
  if (fullRangeRow > 1) {
    // Group Validation (Col 7 / G)
    const groupRange = targetSheet.getRange(2, 7, fullRangeRow - 1, 1);
    const groupRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(["Composite Portraits", "Folie à Deux", "Crossbred Songbirds"], true)
      .setAllowInvalid(false)
      .build();
    groupRange.setDataValidation(groupRule);

    // Best Validation (Col 6 / F)
    const bestRange = targetSheet.getRange(2, 6, fullRangeRow - 1, 1);
    const bestRule = SpreadsheetApp.newDataValidation()
      .requireNumberBetween(7, 13)
      .setAllowInvalid(false)
      .build();
    bestRange.setDataValidation(bestRule);
  }
  
  targetSheet.setColumnWidth(1, 80);
  targetSheet.setColumnWidth(2, 250);
  targetSheet.setColumnWidth(7, 160);

  SpreadsheetApp.getUi().alert(`Processed ${data.length} rows. Found ${processedRows.length} unique blends.`);
}
