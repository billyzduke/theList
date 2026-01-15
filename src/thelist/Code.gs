var BLENDED_WITH = {
  'HEADER_NAME': "blended with…",
  'RAW': {
    'SHEET_NAME': "blendus synced raw",
    'COL': 0,
    'ROW_START': 2
  },
  'PRETTY':{
    'SHEET_NAME': "blendus synced pretty",
    'COL': 0,
    'ROW_START': 3
  }
}
var ARTIST = {
  'HEADER_NAME': "aka/artist"
}

// --- 1. ONOPEN (Now Auto-Syncs) ---
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Link Tools')
    .addItem('Sync & Link "blended with…" (From Raw)', 'syncFromRaw') // Manual click = Not silent
    .addItem('Find Unpaired Blend Partners', 'findBrokenLinks')
    .addItem('Find Orphaned Artists (Unblended)', 'findOrphanedArtists')
    .addToUi();

  // Automatically run the sync when the file loads
  // We pass 'true' to enable Silent Mode (no popup alerts)
  syncFromRaw(true);
}

function onEdit(e) {
  var cell = e.range;
  var sheet = cell.getSheet();
  var name = sheet.getName();

  // Logic for manual edits 
  if (name === BLENDED_WITH.PRETTY.SHEET_NAME) {

    var blendedCol = getColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 
    // If column not found, or the edited cell isn't in that column, stop.
    if (blendedCol === -1 || cell.getColumn() !== blendedCol) {
      return;
    }

    // 3. Ignore Header Rows (assuming data starts Row 3)
    if (cell.getRow() < BLENDED_WITH.PRETTY.ROW_START) return;
    
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

    // *** RECIPROCAL LINKIFY ***
    // We run this BEFORE linkifying the current cell, so both happen smoothly.
    updateReciprocalLinks(cell, selfValue, selectedValue, blendedCol);

    applyLinksToRange(cell);
    highlightChipDuplicates(sheet);

  } else {
    if (name === "blendus og") {
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
      var hexTest = new RegExp("^[A-F0-9]{6}$").test(e.value);
      // console.info(hexTest);
      if (hexTest) {
        cell.setBackground('#' + e.value);
        return; // STOP! Do not run the rest of the script.
      }
    }
  }
}

// --- 2. UPDATED SYNC FUNCTION (With Silent Mode & Row 2 Fix) ---
function syncFromRaw(silent) {
  // Check if 'silent' was passed as true. If undefined (menu click), it is false.
  var isSilent = (silent === true);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var targetSheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  var sourceSheet = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);
  
  if (!targetSheet || !sourceSheet) {
    if (!isSilent) SpreadsheetApp.getUi().alert("Sheet not found! Check the names.");
    return;
  }
  
  var rawCol = getColumnByName(sourceSheet, BLENDED_WITH.HEADER_NAME); 
  var blendedCol = getColumnByName(targetSheet, BLENDED_WITH.HEADER_NAME); 

  var lastRowRaw = sourceSheet.getLastRow();
  // Math Fix: (lastRow - StartRow + 1) to capture the exact count
  var totalRows = lastRowRaw - BLENDED_WITH.RAW.ROW_START + 1;

  if (totalRows < 1) return; // Nothing to sync

  // 1. Fetch from Raw Sheet (Using your Row 2 / Col 22 logic)
  var rawValues = sourceSheet.getRange(BLENDED_WITH.RAW.ROW_START, rawCol, totalRows, 1).getValues();
  
  // 2. Define Target on Pretty Sheet (Col Y)
  var targetRange = targetSheet.getRange(BLENDED_WITH.PRETTY.ROW_START, blendedCol, rawValues.length, 1);

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

// --- 4. CORE LINKING LOGIC ---
function applyLinksToRange(range) {
  var sheet = range.getSheet();
  var values = range.getValues();
  
  var lastRow = sheet.getLastRow();
  
  // *** FIXED LINE BELOW ***
  // We now TRIM the source values too, to prevent hidden spaces from breaking matches.
  var sourceValues = sheet.getRange(BLENDED_WITH.PRETTY.ROW_START, 1, lastRow - (BLENDED_WITH.PRETTY.ROW_START - 1), 1).getValues().flat()
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
        var rowNum = sourceIndex + 3; 
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

/**
 * RECIPROCAL LINKING LOGIC
 * If Row A selects Row B, this function goes to Row B and selects Row A.
 */
function updateReciprocalLinks(sourceRange, sourceName, targetNamesString, targetColIndex) {
  var sheet = sourceRange.getSheet();
  var lastRow = sheet.getLastRow();
  
  // 1. Get the list of all names in Col A to map names -> row numbers
  //    (We rely on the Ghost List order or Raw order? We rely on Col A order)
  var allNames = sheet.getRange(BLENDED_WITH.PRETTY.ROW_START, 1, lastRow - (BLENDED_WITH.PRETTY.ROW_START - 1), 1).getValues().flat().map(String);
  
  // 2. Parse the target names (the ones just selected)
  if (!targetNamesString) return;
  var targets = targetNamesString.split(",").map(function(s) { return s.trim(); });
  
  // 3. Loop through each person we just selected
  targets.forEach(function(targetName) {
    if (targetName === "") return;
    
    // Find the row number for this target person
    var targetIndex = allNames.indexOf(targetName);
    
    if (targetIndex !== -1) {
      var targetRowNum = targetIndex + BLENDED_WITH.PRETTY.ROW_START; // +3 because data starts at A3
      
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

/**
 * Finds the column number by its header name (in Row 1).
 * CHECKS THE GLOBAL VARIABLE FIRST TO SEE IF A POSITIVE INTEGER VALUE HAS ALREADY BEEN SET
 * Returns -1 if not found.
 */
function getColumnByName(sheet, headerName) {
  var sheetName = sheet.getName();
  if (sheetName.endsWith("raw")) {
    if (!BLENDED_WITH.RAW.COL || BLENDED_WITH.RAW.COL < 0) BLENDED_WITH.RAW.COL = getColumnIndexByName(sheet, headerName)
    return BLENDED_WITH.RAW.COL
  }
  if (sheetName.endsWith("pretty")) {
    if (!BLENDED_WITH.PRETTY.COL || BLENDED_WITH.PRETTY.COL < 0) BLENDED_WITH.PRETTY.COL = getColumnIndexByName(sheet, headerName)
    return BLENDED_WITH.PRETTY.COL
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

/**
 * AUDIT FUNCTION
 * Scans Column 'Blended With'.
 * If Row A links to Row B, checks if Row B links back to Row A.
 * Highlights broken links in RED.
 */
function findBrokenLinks() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  var lastRow = sheet.getLastRow();
  
  var blendedCol = getColumnByName(sheet, BLENDED_WITH.HEADER_NAME);
  if (blendedCol === -1) {
    SpreadsheetApp.getUi().alert("Column not found.");
    return;
  }

  // 1. Get Normalized Data
  var nameValues = sheet.getRange(BLENDED_WITH.PRETTY.ROW_START, 1, lastRow - 2, 1)
    .getValues().flat().map(function(s) { return s.toString().normalize("NFC"); });

  var linkRange = sheet.getRange(BLENDED_WITH.PRETTY.ROW_START, blendedCol, lastRow - 2, 1);
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

/**
 * CHIP-ONLY DUPLICATE HIGHLIGHTER
 * Only runs on complex columns where native Conditional Formatting fails.
 */
function highlightChipDuplicates(sheet) {
  // --- CONFIGURATION ---
  var DUPE_CONFIG = [
    { 
      colIndex: getColumnIndexByName(sheet, ARTIST.HEADER_NAME),       // Column E (The Chip Column)
      color: "#bfdfcc"  
    }
    // If you ever have another CHIP column, add it here:
    // { colIndex: 8, color: "#FFF2CC" }
  ];
  
  var lastRow = sheet.getLastRow();
  if (lastRow < BLENDED_WITH.PRETTY.ROW_START) return;

  DUPE_CONFIG.forEach(function(rule) {
    var colIndex = rule.colIndex;
    var highlightColor = rule.color;
    
    var range = sheet.getRange(BLENDED_WITH.PRETTY.ROW_START, colIndex, lastRow - BLENDED_WITH.PRETTY.ROW_START + 1, 1);
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

/**
 * AUDIT: FIND ORPHANED ARTISTS
 * Scans the sheet for rows that have an Artist (Col E) 
 * but NO Blended connections (Target Col).
 * useful for finding folders/pairs you skipped during manual entry.
 */
function findOrphanedArtists() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  // --- CONFIG ---
  var NAME_COL_INDEX = 1;    // Column A (The Name)
  var ARTIST_COL_INDEX = getColumnIndexByName(sheet, ARTIST.HEADER_NAME);  
  var BLEND_COL_INDEX = getColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 

  var START_ROW = BLENDED_WITH.PRETTY.ROW_START;
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


/**
 * ============================================================================
 * PROJECT: BLENDUS SYNC & LINK SYSTEM
 * ============================================================================
 * * 1. CONFIGURATION (Top of file)
 * - Controls Sheet Names, Column Headers, and Import Settings.
 * - To change the target column, change 'HEADER_NAME'.
 * * 2. SYNC FROM RAW (syncFromRaw)
 * - Imports data from the 'RAW' sheet to the 'PRETTY' sheet.
 * - Fixes the "Missing Apostrophe" bug by escaping values.
 * - Auto-runs on Sheet Open (Silent Mode).
 * - Can be run manually from the "Link Tools" menu.
 * * 3. RECIPROCAL LINKING (onEdit -> updateReciprocalLinks)
 * - If you add "Björk" to "The Sugarcubes" row, this script finds "Björk"s row
 * and automatically adds "The Sugarcubes" to it.
 * - Prevents self-linking errors.
 * * 4. HYPERLINKER (applyLinksToRange)
 * - Converts names inside the 'Blended With' column into clickable links
 * that jump to that person's specific row in Column A.
 * - Handles comma-separated lists (Multiple links per cell).
 * * 5. SOCIAL MEDIA URLs (onEdit -> Path B)
 * - Converts various incomplete URL data (Instagram, YouTube, etc.) in Cols 19-24 into functioning hyperlinks.
 * * 6. DUPLICATE HIGHLIGHTER (highlightChipDuplicates)
 * - Replaces Conditional Formatting for speed.
 * - Scans Column E. If a "Chip" (Band Member) appears in more than one row,
 * highlights all occurrences in RED.
 * - Handles Multi-Select chips ("Band A, Band B").
 * * 7. AUDIT TOOL (findBrokenLinks)
 * - "Link Tools > Find Broken Links"
 * - Scans the whole sheet for One-Way blend links (A links to B, B ignores A).
 * - Generates a popup report of specific errors.
 * ============================================================================
 */
