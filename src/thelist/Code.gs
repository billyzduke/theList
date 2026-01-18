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
    .createMenu('inhumantools')
    .addItem('Sync & Link "blended with…" (From Raw)', 'syncFromRaw') // Manual click = Not silent
    .addItem('Find Unpaired Blend Partners', 'findBrokenLinks')
    .addItem('Find Orphaned Artists (Unblended)', 'findOrphanedArtists')
    .addSeparator() // Optional: Adds a line to separate the Export tool
    .addItem('Export blend-data (.csv)', 'generateBlendDataExport')
    .addSeparator() 
    .addItem('Set Up "Blends Registry" (new sheet)', 'setupBlendRegistry')
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
  if (sheet.getName() !== "blends") return;

  // Run the sync
  syncRegistryToPeople();
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
      if (name === 'blends') {
        syncRegistryToPeople()
      }

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
 * EXPORT FOR GEPHI
 * Creates a new sheet named "blend-data" with a simple Source,Target list.
 * Run this, then File > Download > CSV on the new sheet.
 */
function generateBlendDataExport() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(BLENDED_WITH.PRETTY.SHEET_NAME);
  
  // --- CONFIG ---
  var NAME_COL_INDEX = 1;    // Column A
  var BLEND_COL_INDEX = getColumnByName(sheet, BLENDED_WITH.HEADER_NAME); 
  var START_ROW = BLENDED_WITH.PRETTY.ROW_START;
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
  const TARGET_SHEET_NAME = "blends";
  
  // COLUMN INDICES (0-based)
  const COL_NAME = 0;       // Column A: Name
  const COL_OCCUPATION = getColumnIndexByName(SOURCE_SHEET_NAME, "whaddayado"); // Column E: Occupation
  const COL_BLENDS = getColumnByName(SOURCE_SHEET_NAME, BLENDED_WITH.HEADER_NAME) - 1;  // Column X: The comma-separated list of partners
  
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
  const data = sourceSheet.getRange(2, 1, lastRow - 1, sourceSheet.getLastColumn()).getValues();
  
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

/**
 * Scans Column A of the 'blends' sheet.
 * Sets background to the hex code value.
 * Sets text color to Black or White based on contrast.
 */
function colorizeHexColumn() {
  const SHEET_NAME = 'blends';
  const HEX_COL_INDEX = 1; // Column A
  const START_ROW = 3;     // Skip header
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME);
  
  if (!sheet) return;

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

/**
 * REVERSE SYNC: Reads 'blends' Registry -> Updates 'blendus synced raw'.
 * USES DYNAMIC COLUMN HEADERS.
 */
function syncRegistryToPeople() {
  const REGISTRY_SHEET_NAME = "blends"
  const REGISTRY_BLENDEES_HEADER = "blendees"; 
  const NAME_HEADER = "NAME";  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const rawSheet = ss.getSheetByName(BLENDED_WITH.RAW.SHEET_NAME);  
  const regSheet = ss.getSheetByName(REGISTRY_SHEET_NAME);

  if (!regSheet || !rawSheet) {
    console.error("Sync Error: Missing sheets.");
    return;
  }  

  // 1. DYNAMICALLY FIND COLUMN INDEXES
  const regHeaders = regSheet.getRange(1, 1, 1, regSheet.getLastColumn()).getValues()[0];
  const rawHeaders = rawSheet.getRange(1, 1, 1, rawSheet.getLastColumn()).getValues()[0];

  const regBlendColIdx = regHeaders.indexOf(REGISTRY_BLENDEES_HEADER);
  const rawNameColIdx = rawHeaders.indexOf(NAME_HEADER);
  const rawTargetColIdx = rawHeaders.indexOf(BLENDED_WITH.HEADER_NAME);

  // Safety Check: Did we find all headers?
  if (regBlendColIdx === -1 || rawNameColIdx === -1 || rawTargetColIdx === -1) {
    const missing = [];
    if (regBlendColIdx === -1) missing.push(`'${REGISTRY_BLENDEES_HEADER}' in ${REGISTRY_SHEET_NAME}`);
    if (rawNameColIdx === -1) missing.push(`'${NAME_HEADER}' in ${BLENDED_WITH.RAW.SHEET_NAME}`);
    if (rawTargetColIdx === -1) missing.push(`'${BLENDED_WITH.HEADER_NAME}' in ${BLENDED_WITH.RAW.SHEET_NAME}`);
    SpreadsheetApp.getUi().alert(`Error: Could not find headers: ${missing.join(", ")}`);
    return;
  }

  // 2. READ REGISTRY & BUILD MAP
  // Get all data (skip header row)
  const regData = regSheet.getRange(2, 1, regSheet.getLastRow() - 1, regSheet.getLastColumn()).getValues();
  
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
  const peopleData = rawSheet.getRange(2, 1, rawSheet.getLastRow() - 1, rawSheet.getLastColumn()).getValues();
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
  rawSheet.getRange(2, rawTargetColIdx + 1, outputValues.length, 1).setValues(outputValues);
  
  // Optional: Log status
  console.log("Sync Complete.");
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
