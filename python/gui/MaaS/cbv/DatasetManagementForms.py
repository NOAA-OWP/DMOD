from django import forms
from enum import Enum
from functools import partial

from dmod.core.meta_data import DataCategory, DataFormat

# typing imports
from typing import Optional

# form field type alias
# correspond to `dmod.core.meta_data.StandardDatasetIndex``
_Unknown = forms.CharField
_Time = partial(
    forms.DateTimeField,
    widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    # TODO: this should be removed once we upgrade django versions >= 3.1 (tracked by #209)
    input_formats=["%Y-%m-%dT%H:%M"],
)
_CatchmentId = forms.CharField
_DataId = forms.CharField
_HydrofabricId = forms.CharField
_Length = forms.IntegerField
_GlobalChecksum = forms.CharField
_ElementId = forms.CharField


class FormNameMixIn:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            # input field have id's of form: `id_{{field instance var name}}_{{form name}}
            visible.field.widget.attrs["id"] = f"{visible.auto_id}_{self.form_name()}"
            visible.field.widget.attrs["class"] = self.form_name()

    def form_name(self) -> str:
        """returns class name of form"""
        return type(self).__name__


class DatasetForm(FormNameMixIn, forms.Form):
    name = forms.CharField(max_length=100, label="Dataset Name")
    category = forms.ChoiceField(
        choices=[(f.name, f.name.title()) for f in DataCategory],
        label="Dataset Category",
    )
    data_format = forms.ChoiceField(
        choices=[(f.name, f.name) for f in DataFormat], label="Data Format"
    )


class AORC_CSV(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId()
    start_time = _Time(label="Start Datetime")
    end_time = _Time(
        label="End Datetime",
        # TODO: note if end times are inclusive.
        # TODO: note that all datetimes are naive UTC time.
        # help_text="",
    )


class NETCDF_FORCING_CANONICAL(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")


class NETCDF_AORC_DEFAULT(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")


class NGEN_OUTPUT(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")
    data_id = _DataId


class NGEN_REALIZATION_CONFIG(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")
    data_id = _DataId


class NGEN_GEOJSON_HYDROFABRIC(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    hydrofabric_id = _HydrofabricId
    data_id = _DataId


class NGEN_PARTITION_CONFIG(FormNameMixIn, forms.Form):
    data_id = _DataId
    hydrofabric_id = _HydrofabricId
    length = _Length


class BMI_CONFIG(FormNameMixIn, forms.Form):
    global_checksum = _GlobalChecksum
    data_id = _DataId


class NWM_OUTPUT(FormNameMixIn, forms.Form):
    catchment_id = _CatchmentId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")
    data_id = _DataId


class NWM_CONFIG(FormNameMixIn, forms.Form):
    element_id = _ElementId
    start_time = _Time(label="Start Datetime")
    end_time = _Time(label="End Datetime")
    data_id = _DataId


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
