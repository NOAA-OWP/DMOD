
function titleCase(str) {
    return str.replaceAll("_", " ").toLowerCase().split(' ').map(function(word) {
        return word.replace(word[0], word[0].toUpperCase());
    }).join(' ');
}

function loadFabricNames() {
    $.ajax(
        {
            url: "fabric/names",
            type: 'GET',
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                if (result != null) {
                    result['fabric_names'].forEach(function(name) {
                        $("#fabric-selector").append("<option value='" + name + "'>" + titleCase(name) + "</option>");
                    });
                    $("#fabric-selector option")[0].setAttribute("selected", "");
                    loadFabricDomain();
                }
            }
        }
    );
}

function loadFabricTypes() {
    $.ajax(
        {
            url: "fabric/types",
            type: 'GET',
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                if (result != null) {
                    result['fabric_types'].forEach(function(name) {
                        $("#fabric-type-selector").append("<option value='" + name + "'>" + titleCase(name) + "</option>");
                    });
                    $("#fabric-type-selector option")[0].setAttribute("selected", "");
                    loadFabricDomain();
                }
            }
        }
    );
}

function insertOptionInOrder(option, newParentSelect) {
    let next_index;
    let current_index = 0;
    let next_size = 200;

    next_index = current_index + next_size;
    while (next_index < newParentSelect.options.length) {
        if (parseInt(option.value) < parseInt(newParentSelect.options[next_index].value)) {
            break;
        }
        else {
            current_index = next_index;
            next_index = current_index + next_size;
        }
    }

    for (current_index; current_index < newParentSelect.options.length; current_index++) {
        if (parseInt(option.value) < parseInt(newParentSelect.options[current_index].value)) {
            newParentSelect.options.add(option, newParentSelect.options[current_index]);
            return;
        }
    }
    newParentSelect.appendChild(option);
}

function addDomainChoicesOption(values) {
    let select = document.getElementById('domainChoices');
    for (let optionIndex = 0; optionIndex < values.length; optionIndex++) {
        const option = document.createElement('option');
        option.value = values[optionIndex].substring(4);
        option.innerHTML = values[optionIndex];
        insertOptionInOrder(option, select);
    }
}

function controlSelectAdd() {
    let choices = document.getElementById('domainChoices');
    let selected = document.getElementById('domainSelections');

    for (let optionIndex = choices.options.length - 1; optionIndex >=0; optionIndex--) {
        let opt = choices.options[optionIndex];
        if (opt.selected) {
            opt.selected = false;
            choices.removeChild(opt);
            insertOptionInOrder(opt, selected);
        }
    }
}

function controlSelectRemove() {
    let choices = document.getElementById('domainChoices'),
        selected = document.getElementById('domainSelections'),
        opt;

    for (let optionIndex = selected.options.length - 1; optionIndex >=0; optionIndex--) {
        opt = selected.options[optionIndex];
        if (opt.selected) {
            opt.selected = false;
            selected.removeChild(opt);
            insertOptionInOrder(opt, choices);
        }
    }
}

function controlSelectAll() {
    let choices = document.getElementById('domainChoices');
    let selected = document.getElementById('domainSelections');
    let opt;

    for (let optionIndex = choices.options.length - 1; optionIndex >= 0 ; optionIndex--) {
        opt = choices.options[optionIndex];
        if (opt.selected) {
            opt.selected = false;
        }
        choices.removeChild(opt);
        insertOptionInOrder(opt, selected);
    }
}

function controlSelectClear() {
    let choices = document.getElementById('domainChoices');
    let selected = document.getElementById('domainSelections');
    let opt;

    for (let optionIndex = selected.options.length - 1; optionIndex >= 0 ; optionIndex--) {
        opt = selected.options[optionIndex];
        if (opt.selected) {
            opt.selected = false;
        }
        selected.removeChild(opt);
        insertOptionInOrder(opt, choices);
    }
}

function loadFabricDomain(event) {
    let name = $("#fabric-selector").val();
    let type = "catchment";  //$("#fabric-type-selector").val(),
    let catLists = [document.getElementById('domainChoices'),
        document.getElementById('domainSelections')];
    let loadingOverDiv = document.getElementById('loadCatsOverlay');

    catLists[0].style.display = "none";
    loadingOverDiv.style.display = "block";

    $("input[name=fabric]").val(name);

    // Clear any existing <option> tags from within "domainChoices" <select>
    for (let catchmentSelect of catLists) {
        for (let optionIndex = catchmentSelect.options.length - 1; optionIndex >= 0; optionIndex--) {
            catchmentSelect.remove(optionIndex);
        }
    }

    let url = "fabric/" + name;

    $.ajax(
        {
            url: url,
            type: "GET",
            data: {"fabric_type": type, "id_only": true},
            error: function(xhr, status, error) {
                console.error(error);
                catLists[0].style.display = "block";
                loadingOverDiv.style.display = "none";
            },
            success: function(result, status, xhr) {
                if (result) {
                    addDomainChoicesOption(result);
                }
                catLists[0].style.display = "block";
                loadingOverDiv.style.display = "none";
            }
        }
    )
}

function submitCatchments(event) {
    let featuresToConfigure = [];
    let selections = document.getElementById('domainSelections');
    let selectForm = document.getElementById('location-selection-form');

    for (let optionIndex = 0; optionIndex < selections.options.length; optionIndex++) {
        featuresToConfigure.push('cat-' + selections.options[optionIndex].value)
    }

    if (featuresToConfigure.length == 0) {
        event.preventDefault();
        alert("Select a location to configure before continuing.");
        return;
    }

    selectForm['feature-ids'].value = featuresToConfigure.join("|");
    selectForm['framework'].value = 'ngen';
    selectForm.submit();
}