from django import forms
from enum import Enum
from functools import partial

from dmod.core.meta_data import DataCategory, DataFormat
from django.conf import settings

from .js_utils import start_end_time_validation

# typing imports
from typing import Optional

# form field type alias
# correspond to `dmod.core.meta_data.StandardDatasetIndex``
def _time(start_time_id: str, end_time_id: str):
    return partial(
        forms.DateTimeField,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "onchange": start_end_time_validation(start_time_id, end_time_id),
            }
        ),
        # TODO: this should be removed once we upgrade django versions >= 3.1 (tracked by #209)
        input_formats=[settings.DATE_TIME_FORMAT],
    )


_Unknown = forms.CharField
_CatchmentId = forms.CharField
_DataId = forms.CharField
_HydrofabricId = forms.CharField
_Length = forms.IntegerField
_GlobalChecksum = forms.CharField
_ElementId = forms.CharField
_Files = partial(
    forms.FileField,
    widget=forms.ClearableFileInput(
        attrs={
            'multiple': True,
            # filename cannot contain underscore (_)
            "oninput": """((el) => {
            const files = el.files;

            for (let {name} of files){
                // filenames cannot include _'s.
                //if (name.includes('_')){

                    // see constraint validation API for more detail (https://developer.mozilla.org/en-US/docs/Web/API/Constraint_validation)
                //    el.setCustomValidity('Filename cannot contain underscores \"_\"');
                //    return;
                //}

                // valid input
                el.setCustomValidity('');
            }

            })(this)"""
        }
    ),
)


class FormNameMixIn:
    def form_name(self) -> str:
        """returns class name of form"""
        return type(self).__name__


class DynamicFormMixIn:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            # input field have id's of form: `id_{{field instance var name}}_{{form name}}
            visible.field.widget.attrs["id"] = f"{visible.auto_id}_{self.form_name()}"
            visible.field.widget.attrs["class"] = self.form_name()
            visible.field.widget.attrs["style"] = "display: none;"
            visible.field.widget.attrs["disabled"] = "true"


class DatasetForm(FormNameMixIn, forms.Form):
    name = forms.CharField(max_length=100, label="Dataset Name")
    category = forms.ChoiceField(
        choices=[(f.name, f.name.title()) for f in DataCategory],
        label="Dataset Category",
    )
    data_format = forms.ChoiceField(
        choices=[("---", "---")] + [(f.name, f.name) for f in DataFormat],
        label="Data Format",
        widget=forms.Select(
            attrs={
                # when selection changes, unhide and enable the form fields and labels for the
                # corresponding DataFormat. form fields and labels have an html class name of their
                # DataFormat. i.e. <input type="datetime-local" class="NETCDF_AORC_DEFAULT" ... >
                "onchange": """((name) => {
                    // remove previously active fields, if any
                    const active_fields = document.querySelectorAll('.active_field')
                    active_fields.forEach(el => {

                        // disable field, hide it, and remove flag class, 'active_field'
                        el.setAttribute('disabled', true)
                        el.style.display = 'none'
                        el.classList.remove('active_field')
                        })

                    const els_with_class = document.querySelectorAll(`.${name}`)
                    els_with_class.forEach(el => {

                        // enable field, hide it, and remove flag class, 'active_field'
                        el.removeAttribute('disabled')
                        el.style.display = 'block'
                        el.classList.add('active_field')
                    })
            })(this.value)"""
            }
        ),
    )


class AORC_CSV(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time("id_start_time_AORC_CSV", "id_end_time_AORC_CSV")(
        label="Start Datetime"
    )
    end_time = _time("id_start_time_AORC_CSV", "id_end_time_AORC_CSV")(
        label="End Datetime"
    )
    # TODO: note if end times are inclusive.
    # TODO: note that all datetimes are naive UTC time.
    # help_text="",
    # )
    files = _Files()


class NETCDF_FORCING_CANONICAL(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time(
        "id_start_time_NETCDF_FORCING_CANONICAL", "id_end_time_NETCDF_FORCING_CANONICAL"
    )(label="Start Datetime")
    end_time = _time(
        "id_start_time_NETCDF_FORCING_CANONICAL", "id_end_time_NETCDF_FORCING_CANONICAL"
    )(label="End Datetime")
    files = _Files()


class NETCDF_AORC_DEFAULT(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time(
        "id_start_time_NETCDF_AORC_DEFAULT", "id_end_time_NETCDF_AORC_DEFAULT"
    )(label="Start Datetime")
    end_time = _time(
        "id_start_time_NETCDF_AORC_DEFAULT", "id_end_time_NETCDF_AORC_DEFAULT"
    )(label="End Datetime")
    files = _Files()


class NGEN_OUTPUT(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time("id_start_time_NGEN_OUTPUT", "id_end_time_NGEN_OUTPUT")(
        label="Start Datetime"
    )
    end_time = _time("id_start_time_NGEN_OUTPUT", "id_end_time_NGEN_OUTPUT")(
        label="End Datetime"
    )
    data_id = _DataId()
    files = _Files()


class NGEN_REALIZATION_CONFIG(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time(
        "id_start_time_NGEN_REALIZATION_CONFIG", "id_end_time_NGEN_REALIZATION_CONFIG"
    )(label="Start Datetime")
    end_time = _time(
        "id_start_time_NGEN_REALIZATION_CONFIG", "id_end_time_NGEN_REALIZATION_CONFIG"
    )(label="End Datetime")
    data_id = _DataId()
    files = _Files()


class NGEN_GEOJSON_HYDROFABRIC(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    hydrofabric_id = _HydrofabricId()
    data_id = _DataId()
    files = _Files()


class NGEN_PARTITION_CONFIG(DynamicFormMixIn, FormNameMixIn, forms.Form):
    data_id = _DataId()
    hydrofabric_id = _HydrofabricId
    length = _Length()
    files = _Files()


class BMI_CONFIG(DynamicFormMixIn, FormNameMixIn, forms.Form):
    global_checksum = _GlobalChecksum()
    data_id = _DataId()
    files = _Files()


class NWM_OUTPUT(DynamicFormMixIn, FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _time("id_start_time_NWM_OUTPUT", "id_end_time_NWM_OUTPUT")(
        label="Start Datetime"
    )
    end_time = _time("id_start_time_NWM_OUTPUT", "id_end_time_NWM_OUTPUT")(
        label="End Datetime"
    )
    data_id = _DataId()
    files = _Files()


class NWM_CONFIG(DynamicFormMixIn, FormNameMixIn, forms.Form):
    element_id = _ElementId()
    start_time = _time("id_start_time_NWM_CONFIG", "id_end_time_NWM_CONFIG")(
        label="Start Datetime"
    )
    end_time = _time("id_start_time_NWM_CONFIG", "id_end_time_NWM_CONFIG")(
        label="End Datetime"
    )
    data_id = _DataId()
    files = _Files()


class DatasetFormatForm(Enum):
    AORC_CSV = AORC_CSV
    NETCDF_FORCING_CANONICAL = NETCDF_FORCING_CANONICAL
    NETCDF_AORC_DEFAULT = NETCDF_AORC_DEFAULT
    NGEN_OUTPUT = NGEN_OUTPUT
    NGEN_REALIZATION_CONFIG = NGEN_REALIZATION_CONFIG
    NGEN_GEOJSON_HYDROFABRIC = NGEN_GEOJSON_HYDROFABRIC
    NGEN_PARTITION_CONFIG = NGEN_PARTITION_CONFIG
    BMI_CONFIG = BMI_CONFIG
    NWM_OUTPUT = NWM_OUTPUT
    NWM_CONFIG = NWM_CONFIG

    @staticmethod
    def get_form_from_name(name: str) -> Optional[forms.Form]:
        try:
            return DatasetFormatForm[name].value
        except KeyError:
            return None
