var BLENDED_WITH = {
  'HEADER_NAME': "blended with…",
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
    if (!BLENDED_WITH.RAW.WITH_COL_INDEX || BLENDED_WITH.RAW.WITH_COL_INDEX < 0) BLENDED_WITH.RAW.WITH_COL_INDEX = getColumnIndexByName(sheet, headerName)
    //SpreadsheetApp.getUi().alert("sheet = '"+sheet+"'\nheaderName = '"+headerName+"'\nBLENDED_WITH.RAW.WITH_COL_INDEX = "+BLENDED_WITH.RAW.WITH_COL_INDEX);
    return BLENDED_WITH.RAW.WITH_COL_INDEX
  }
  if (sheetName.endsWith("pretty")) {
    if (!BLENDED_WITH.PRETTY.WITH_COL_INDEX || BLENDED_WITH.PRETTY.WITH_COL_INDEX < 0) BLENDED_WITH.PRETTY.WITH_COL_INDEX = getColumnIndexByName(sheet, headerName)
    //SpreadsheetApp.getUi().alert("sheet = '"+sheet+"'\nheaderName = '"+headerName+"'\nBLENDED_WITH.PRETTY.WITH_COL_INDEX = "+BLENDED_WITH.PRETTY.WITH_COL_INDEX);
    return BLENDED_WITH.PRETTY.WITH_COL_INDEX
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
    .addItem('Sync & Link "blended with…" (From Raw to Pretty)', 'syncFromRaw') // Manual click = Not silent
    .addItem('Find Unpaired Blend Partners', 'findBrokenLinks')
    .addItem('Find Orphaned Artists (Unblended)', 'findOrphanedArtists')
    .addSeparator() // Optional: Adds a line to separate the Export tool
    .addItem('Generate Missing xIDENT values for raw Ladies', 'generateMissingIDs')
    .addItem('Export blend-data (.csv)', 'generateBlendDataExport')
    .addSeparator() 
    // .addItem('Set Up "Blends Registry" (new sheet)', 'setupBlendRegistry')
    .addItem('Refresh Hex Colors', 'colorizeHexColumn')
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
  if (sheet.getName() !== BLENDED_WITH.REGISTRY.SHEET_NAME) return;

  // Run the sync
  syncRegistryToPeople();
}

function onEdit(e) {
  var cell = e.range;
  var sheet = cell.getSheet();
  var name = sheet.getName();

  // Logic for manual edits 
  if (name === BLENDED_WITH.PRETTY.SHEET_NAME) {

    var blendedCol = getBlendedWithColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 
    // If column not found, or the edited cell isn't in that column, stop.
    if (blendedCol === -1 || cell.getColumn() !== blendedCol) {
      return;
    }

    // 3. Ignore Header Rows (assuming data starts Row 3)
    if (cell.getRow() < BLENDED_WITH.PRETTY.DATA_START_ROW) return;
    
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
    if (name === BLENDED_WITH.OG.SHEET_NAME) { // THE ORIGINAL MANUALLY EDITED SHEET, NOW WELL OUT OF DATE
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
      // if (name === BLENDED_WITH.REGISTRY.SHEET_NAME) {
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
  // --- 2. UPDATED SYNC FUNCTION (With Silent Mode & Row 2 Fix) ---
  // Check if 'silent' was passed as true. If undefined (menu click), it is false.
  var isSilent = (silent === true);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var targetSheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  var sourceSheet = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);
  
  if (!targetSheet || !sourceSheet) {
    if (!isSilent) SpreadsheetApp.getUi().alert("Sheet not found! Check the names.");
    return;
  }
  
  var rawCol = getBlendedWithColumnByName(sourceSheet, BLENDED_WITH.HEADER_NAME); 
  var blendedCol = getBlendedWithColumnByName(targetSheet, BLENDED_WITH.HEADER_NAME); 

  var lastRowRaw = sourceSheet.getLastRow();
  // Math Fix: (lastRow - StartRow + 1) to capture the exact count
  var totalRows = lastRowRaw - BLENDED_WITH.RAW.DATA_START_ROW + 1;

  if (totalRows < 1) return; // Nothing to sync

  // 1. Fetch from Raw Sheet (Using your Row 2 / Col 22 logic)
  var rawValues = sourceSheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, rawCol, totalRows, 1).getValues();
  
  // 2. Define Target on Pretty Sheet (Col Y)
  var targetRange = targetSheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, blendedCol, rawValues.length, 1);

  // Resets the background to default (white/transparent) to clear old audit warnings.
  targetRange.setBackground(null);
  
  // 3. Paste and Link
  targetRange.setValues(rawValues);
  applyLinksToRange(targetRange);
  highlightChipDuplicates(targetSheet);

  // Only show the alert if this was a manual menu click
  if (!isSilent) {
    SpreadsheetApp.getUi().alert("Synced " + rawValues.length + " rows from Raw Sheet.");
  }
}

function applyLinksToRange(range) {
  // --- 4. CORE LINKING LOGIC ---
  var sheet = range.getSheet();
  var values = range.getValues();
  var lastRow = sheet.getLastRow();
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  
  // *** FIXED LINE BELOW ***
  // We now TRIM the source values too, to prevent hidden spaces from breaking matches.
  var sourceValues = sheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, NAME_COL_INDEX, lastRow - BLENDED_WITH.PRETTY.DATA_START_ROW + 1, 1).getValues().flat()
    .map(function(s) { return s.toString().trim(); });
    
  var sheetId = sheet.getSheetId();

  var richTextOutput = [];

  for (var i = 0; i < values.length; i++) {
    var cellValue = values[i][0];
    
    // Handle empty/null values safely
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
      
      var sourceIndex = sourceValues.indexOf(tag);
      if (sourceIndex !== -1) {
        var rowNum = sourceIndex + BLENDED_WITH.PRETTY.DATA_START_ROW; 
        var url = "#gid=" + sheetId + "&range=A" + rowNum;
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

  // If you want to get rid of the chip formatting on edited cells and just leave blue hyperlinks
  // which doesn't matter since you still have to hover THEN click for hyperlinks inside a cell
  // range.clearDataValidations();
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
  var allNames = sheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, NAME_COL_INDEX, lastRow - BLENDED_WITH.PRETTY.DATA_START_ROW + 1, 1).getValues().flat().map(String);
  
  // 2. Parse the target names (the ones just selected)
  if (!targetNamesString) return;
  var targets = targetNamesString.split(",").map(function(s) { return s.trim(); });
  
  // 3. Loop through each person we just selected
  targets.forEach(function(targetName) {
    if (targetName === "") return;
    
    // Find the row number for this target person
    var targetIndex = allNames.indexOf(targetName);
    
    if (targetIndex !== -1) {
      var targetRowNum = targetIndex + BLENDED_WITH.PRETTY.DATA_START_ROW; // +3 because data starts at A3
      
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
  var DUPE_CONFIG = [
    { 
      colIndex: getColumnIndexByName(sheet, ARTIST.HEADER_NAME),       // Column E (The Chip Column)
      color: "#bfdfcc"  
    }
    // If you ever have another CHIP column, add it here:
    // { colIndex: 8, color: "#FFF2CC" }
  ];
  
  var lastRow = sheet.getLastRow();
  if (lastRow < BLENDED_WITH.PRETTY.DATA_START_ROW) return;

  DUPE_CONFIG.forEach(function(rule) {
    var colIndex = rule.colIndex;
    var highlightColor = rule.color;
    
    var range = sheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, colIndex, lastRow - BLENDED_WITH.PRETTY.DATA_START_ROW + 1, 1);
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
  /**
   * REVERSE SYNC: Reads 'blends' Registry -> Updates 'blendus synced raw'.
   * USES DYNAMIC COLUMN HEADERS.
   */
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const rawSheet = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);  
  const regSheet = ss.getSheetByName(BLENDED_WITH.REGISTRY.SHEET_NAME);

  if (!regSheet || !rawSheet) {
    console.error("Sync Error: Missing sheets.");
    return;
  }  

  // 1. DYNAMICALLY FIND COLUMN INDEXES
  const regHeaders = regSheet.getRange(1, 1, 1, regSheet.getLastColumn()).getValues()[0];
  const rawHeaders = rawSheet.getRange(1, 1, 1, rawSheet.getLastColumn()).getValues()[0];

  const regBlendColIdx = regHeaders.indexOf(BLENDED_WITH.REGISTRY.WITH_COL_NAME);
  const rawNameColIdx = rawHeaders.indexOf("NAME");
  const rawTargetColIdx = rawHeaders.indexOf(BLENDED_WITH.HEADER_NAME);

  // Safety Check: Did we find all headers?
  if (regBlendColIdx === -1 || rawNameColIdx === -1 || rawTargetColIdx === -1) {
    const missing = [];
    if (regBlendColIdx === -1) missing.push(`'${BLENDED_WITH.REGISTRY.WITH_COL_NAME}' in ${BLENDED_WITH.REGISTRY.SHEET_NAME}`);
    if (rawNameColIdx === -1) missing.push(`'NAME' in ${BLENDED_WITH.RAW.SHEET_NAME}`);
    if (rawTargetColIdx === -1) missing.push(`'${BLENDED_WITH.HEADER_NAME}' in ${BLENDED_WITH.RAW.SHEET_NAME}`);
    SpreadsheetApp.getUi().alert(`Error: Could not find headers: ${missing.join(", ")}`);
    return;
  }

  // 2. READ REGISTRY & BUILD MAP
  // Get all data (skip header row)
  const regData = regSheet.getRange(BLENDED_WITH.REGISTRY.DATA_START_ROW, 1, regSheet.getLastRow() - BLENDED_WITH.REGISTRY.DATA_START_ROW + 1, regSheet.getLastColumn()).getValues();
  
  const connections = {}; // { "Miley Cyrus": Set("Dua", "Halsey") }

  regData.forEach(row => {
    const blendString = row[regBlendColIdx]; // Dynamic access
    if (!blendString) return;

    // Split "Miley, Dua" -> ["Miley", "Dua"]
    const participants = blendString.toString().split(",").map(p => p.trim()).filter(p => p);

    // Cross-link everyone
    participants.forEach(person => {
      if (!connections[person]) connections[person] = new Set();
      
      participants.forEach(partner => {
        if (person !== partner) connections[person].add(partner);
      });
    });
  });

  // 3. UPDATE PEOPLE SHEET
  const peopleData = rawSheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, 1, rawSheet.getLastRow() - BLENDED_WITH.RAW.DATA_START_ROW + 1, rawSheet.getLastColumn()).getValues();
  const outputValues = [];

  peopleData.forEach(row => {
    const name = row[rawNameColIdx].toString().trim(); // Dynamic access
    
    if (connections[name]) {
      const sortedPartners = Array.from(connections[name]).sort().join(", ");
      outputValues.push([sortedPartners]);
    } else {
      outputValues.push([""]); // Clear if no blends
    }
  });

  // 4. WRITE BACK
  // We write to the specific target column (index + 1 for 1-based setRange)
  rawSheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, rawTargetColIdx + 1, outputValues.length, 1).setValues(outputValues);
  
  generateMissingIDs();
  // Optional: Log status
  console.log("Sync Complete.");
}

function colorizeHexColumn() {
  /**
   * Scans Column A of the 'blends' sheet.
   * Sets background to the hex code value.
   * Sets text color to Black or White based on contrast.
   */
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(BLENDED_WITH.REGISTRY.SHEET_NAME);
  if (!sheet) return;
  const HEX_COL_INDEX = getColumnIndexByName(sheet, "hexcode"); // Column A
  const START_ROW = BLENDED_WITH.REGISTRY.DATA_START_ROW;     // Skip header

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
  var sheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var lastRow = sheet.getLastRow();
  
  var blendedCol = getBlendedWithColumnByName(sheet, BLENDED_WITH.HEADER_NAME);
  if (blendedCol === -1) {
    SpreadsheetApp.getUi().alert("Column not found.");
    return;
  }

  // 1. Get Normalized Data
  var nameValues = sheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, NAME_COL_INDEX, lastRow - BLENDED_WITH.PRETTY.DATA_START_ROW + 1, 1).getValues().flat().map(function(s) { return s.toString().normalize("NFC"); });

  var linkRange = sheet.getRange(BLENDED_WITH.PRETTY.DATA_START_ROW, blendedCol, lastRow - BLENDED_WITH.PRETTY.DATA_START_ROW + 1, 1);
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
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var ARTIST_COL_INDEX = getColumnIndexByName(sheet, ARTIST.HEADER_NAME);  
  var BLEND_COL_INDEX = getBlendedWithColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 

  var START_ROW = BLENDED_WITH.PRETTY.DATA_START_ROW;
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
  const sheet = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);
  
  if (!sheet) {
    console.error("Sheet not found: " + BLENDED_WITH.RAW.SHEET_NAME);
    return;
  }
  
  // 1. CONFIGURATION
  // Assuming headers are in Row 1. Data starts Row 2.
  const ID_COL_INDEX = getColumnIndexByName(sheet, "xIDENT"); 
  // const NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return; // No data
  
  // Read Col A (IDs) and Col B (Names) in one batch
  const range = sheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, ID_COL_INDEX, lastRow - BLENDED_WITH.RAW.DATA_START_ROW + 1, 2);
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
    sheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, ID_COL_INDEX, updates.length, 1).setValues(updates);
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
  var sheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  
  // --- CONFIG ---
  var NAME_COL_INDEX = getColumnIndexByName(sheet, "NAME"); 
  var BLEND_COL_INDEX = getBlendedWithColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 
  var START_ROW = BLENDED_WITH.PRETTY.DATA_START_ROW;
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

function setupBlendRegistry() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // --- CONFIGURATION ---
  const SOURCE_SHEET_NAME = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);
  const TARGET_SHEET_NAME = BLENDED_WITH.REGISTRY.SHEET_NAME;
  
  // COLUMN INDICES (0-based)
  const COL_NAME = 0;       // Column A: Name
  const COL_OCCUPATION = getColumnIndexByName(SOURCE_SHEET_NAME, "whaddayado"); // Column E: Occupation
  const COL_BLENDS = getBlendedWithColumnByName(SOURCE_SHEET_NAME, BLENDED_WITH.HEADER_NAME) - 1;  // Column X: The comma-separated list of partners
  
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
  const data = sourceSheet.getRange(BLENDED_WITH.RAW.DATA_START_ROW, 1, lastRow - BLENDED_WITH.RAW.DATA_START_ROW + 1, sourceSheet.getLastColumn()).getValues();
  
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
