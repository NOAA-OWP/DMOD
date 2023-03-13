let prototypeTable;

function getRandomInteger(min, max) {
  var adjustment = Math.random() * (max - min + 1);

  var toIntFunction;

  if (adjustment > 0) {
    toIntFunction = Math.floor;
  }
  else {
    toIntFunction = Math.ceil
  }

  return toIntFunction(adjustment) + min;
}

function getRandomNumber(min, max) {
    return (Math.random() * (max - min + 1)) + min;
}

function loadTable() {
    let data = [];

    const rows = getRandomInteger(50, 75);
    const separators = ["-", "_", "@", "#", "$", "%", "&", "*"];

    for (let rowIndex = 0; rowIndex < rows; rowIndex++) {
        const minimum = getRandomNumber(5, 80)
        let maximum = 0;

        while (maximum <= Math.ceil(minimum) + getRandomInteger(10, 20)) {
            maximum = getRandomNumber(55, 125);
        }

        const codeLength = getRandomInteger(2, 4);
        const codeParts = window.crypto.randomUUID().split("-").slice(0, codeLength);
        const separatorIndex = getRandomInteger(0, separators.length - 1);

        const code = codeParts.join(separators[separatorIndex]);

        const rowData = {
            "column0": rowIndex,
            "column1": minimum,
            "column2": maximum,
            "column3": code,
            "column4": getRandomInteger(minimum, maximum),
            "column5": getRandomInteger(8, 30) % 2 === 0
        }

        data.push(rowData);
    }
    evaluationTable = initializeTable(TABLE_NAME, data);
    resizeHandlers.push(evaluationTable.resize)
}

startupScripts.push(loadTable);