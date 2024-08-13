
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
    var next_i, i = 0, next_size = 200;

    next_i = i + next_size;
    while (next_i < newParentSelect.options.length) {
        if (parseInt(option.value) < parseInt(newParentSelect.options[next_i].value)) {
            break;
        }
        else {
            i = next_i;
            next_i = i + next_size;
        }
    }

    for (i; i < newParentSelect.options.length; i++) {
        if (parseInt(option.value) < parseInt(newParentSelect.options[i].value)) {
            newParentSelect.options.add(option, newParentSelect.options[i]);
            return;
        }
    }
    newParentSelect.appendChild(option);
}

function addDomainChoicesOption(values) {
    var select = document.getElementById('domainChoices');
    for (var i = 0; i < values.length; i++) {
        var option = document.createElement('option');
        option.value = values[i].substring(4);
        option.innerHTML = values[i];
        insertOptionInOrder(option, select);
    }
}

function controlSelectAdd() {
    var choices = document.getElementById('domainChoices'),
        selected = document.getElementById('domainSelections');
    for (var i = choices.options.length - 1; i >=0; i--) {
        var opt = choices.options[i];
        if (opt.selected) {
            opt.selected = false;
            choices.removeChild(opt);
            insertOptionInOrder(opt, selected);
        }
    }
}

function controlSelectRemove() {
    var choices = document.getElementById('domainChoices'),
        selected = document.getElementById('domainSelections'),
        i,
        opt;
    for (i = selected.options.length - 1; i >=0; i--) {
        opt = selected.options[i];
        if (opt.selected) {
            opt.selected = false;
            selected.removeChild(opt);
            insertOptionInOrder(opt, choices);
        }
    }
}

function controlSelectAll() {
    var choices = document.getElementById('domainChoices'),
        selected = document.getElementById('domainSelections'),
        i,
        opt;
    for (i = choices.options.length - 1; i >= 0 ; i--) {
        opt = choices.options[i];
        if (opt.selected) {
            opt.selected = false;
        }
        choices.removeChild(opt);
        insertOptionInOrder(opt, selected);
    }
}

function controlSelectClear() {
    var choices = document.getElementById('domainChoices'),
        selected = document.getElementById('domainSelections'),
        i,
        opt;
    for (i = selected.options.length - 1; i >= 0 ; i--) {
        opt = selected.options[i];
        if (opt.selected) {
            opt.selected = false;
        }
        selected.removeChild(opt);
        insertOptionInOrder(opt, choices);
    }
}

function loadFabricDomain(event) {
    var name = $("#fabric-selector").val(),
        type = "catchment", //$("#fabric-type-selector").val(),
        catLists = [document.getElementById('domainChoices'),
                    document.getElementById('domainSelections')],
        loadingOverDiv = document.getElementById('loadCatsOverlay'),
        select,
        l,
        i;

    catLists[0].style.display = "none";
    loadingOverDiv.style.display = "block";

    $("input[name=fabric]").val(name);

    // Clear any existing <option> tags from within "domainChoices" <select>
    for (l = 0; l < catLists.length; l++) {
        select = catLists[l];
        for (i = select.options.length - 1; i >= 0; i--) {
            select.remove(i);
        }
    }

    var url = "fabric/" + name;

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
    var featuresToConfigure = [],
        selections = document.getElementById('domainSelections'),
        selectForm = document.getElementById('location-selection-form'),
        i;

    for (i = 0; i < selections.options.length; i++) {
        featuresToConfigure.push('cat-' + selections.options[i].value)
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