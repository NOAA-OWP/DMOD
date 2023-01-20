from django.db import migrations


def create_premade_formulations(apps, schema_editor):

    Formulation = apps.get_model('MaaS', 'Formulation')
    FormulationParameter = apps.get_model('MaaS', 'FormulationParameter')

    raw_form_details = [
        ('CFE', 'External BMI module implementation of CFE.'),
        ('Multi::Noah_OWP::CFE', 'Combination of external Noah OWP Modular and CFE BMI modules.'),
        ('Multi::Noah_OWP::PET::CFE', 'Combination of external Noah OWP Modular, PET and CFE BMI modules.')
    ]
    formulations = dict([(n, Formulation.objects.create(name=n, description=d)) for n, d in raw_form_details])

    opt_param_desc = 'Optional value to use for {} module {} parameter'

    FormulationParameter.objects.bulk_create([
        #FormulationParameter(name='surface_partitioning_scheme', description='Scheme for surface runoff partitioning', value_type='text', default_value='Schaake', formulation=formulations['CFE']),

        # CFE params
        FormulationParameter(name='BMI Config Dataset', group='CFE', description='Name of dataset containing required BMI initialization files', value_type='text', config_type='dataset', formulation=formulations['CFE']),
        FormulationParameter(name='BMI Init File Pattern', group='CFE', description='The name or pattern for BMI initialization files', value_type='text', config_type='text', default_value='{{id}}_config.ini', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::satdk', group='CFE', description=opt_param_desc.format('CFE', 'satdk'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::maxsmc', group='CFE', description=opt_param_desc.format('CFE', 'maxsmc'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::slope', group='CFE', description=opt_param_desc.format('CFE', 'slope'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::b', group='CFE', description=opt_param_desc.format('CFE', 'b'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::multiplier', group='CFE', description=opt_param_desc.format('CFE', 'multiplier'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::Klf', group='CFE', description=opt_param_desc.format('CFE', 'Klf'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::Kn', group='CFE', description=opt_param_desc.format('CFE', 'Kn'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::Cgw', group='CFE', description=opt_param_desc.format('CFE', 'Cgw'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::expon', group='CFE', description=opt_param_desc.format('CFE', 'expon'), value_type='number', config_type='number', formulation=formulations['CFE']),
        FormulationParameter(name='CFE::max_gw_storage', group='CFE', description=opt_param_desc.format('CFE', 'max_gw_storage'), value_type='number', config_type='number', formulation=formulations['CFE']),

        # Multi::Noah_OWP::CFE params
        FormulationParameter(name='Noah_OWP::BMI Config Dataset', group='Noah_OWP', description='Name of dataset containing required BMI initialization files for Noah OWP', value_type='text', config_type='dataset', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='Noah_OWP::BMI Init File Pattern', group='Noah_OWP', description='The name or pattern for Noah OWP BMI initialization files', value_type='text', config_type='text', default_value='noah-owp-modular-init-{{id}}.namelist.input', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::BMI Config Dataset', group='CFE', description='Name of dataset containing required BMI initialization files for CFE', value_type='text', config_type='dataset', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::BMI Init File Pattern', group='CFE', description='The name or pattern for CFE BMI initialization files', value_type='text', config_type='text', default_value='{{id}}_config.ini', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::satdk', group='CFE', description=opt_param_desc.format('CFE', 'satdk'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::maxsmc', group='CFE', description=opt_param_desc.format('CFE', 'maxsmc'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::slope', group='CFE', description=opt_param_desc.format('CFE', 'slope'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::b', group='CFE', description=opt_param_desc.format('CFE', 'b'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::multiplier', group='CFE', description=opt_param_desc.format('CFE', 'multiplier'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::Klf', group='CFE', description=opt_param_desc.format('CFE', 'Klf'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::Kn', group='CFE', description=opt_param_desc.format('CFE', 'Kn'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::Cgw', group='CFE', description=opt_param_desc.format('CFE', 'Cgw'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::expon', group='CFE', description=opt_param_desc.format('CFE', 'expon'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),
        FormulationParameter(name='CFE::max_gw_storage', group='CFE', description=opt_param_desc.format('CFE', 'max_gw_storage'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::CFE']),

        # Multi::Noah_OWP::PET::CFE params
        FormulationParameter(name='Noah_OWP::BMI Config Dataset', group='Noah_OWP', description='Name of dataset containing required BMI initialization files for Noah OWP', value_type='text', config_type='dataset', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='Noah_OWP::BMI Init File Pattern', group='Noah_OWP', description='The name or pattern for Noah OWP BMI initialization files', value_type='text', config_type='text', default_value='noah-owp-modular-init-{{id}}.namelist.input', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='PET::BMI Config Dataset', group='PET', description='Name of dataset containing required BMI initialization files for PET', value_type='text', config_type='dataset', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='PET::BMI Init File Pattern', group='PET', description='The name or pattern for PET BMI initialization files', value_type='text', config_type='text', default_value='{{id}}_bmi_config.ini', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::BMI Config Dataset', group='CFE', description='Name of dataset containing required BMI initialization files for CFE', value_type='text', config_type='dataset', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::BMI Init File Pattern', group='CFE', description='The name or pattern for CFE BMI initialization files', value_type='text', config_type='text', default_value='{{id}}_bmi_config.ini', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::satdk', group='CFE', description=opt_param_desc.format('CFE', 'satdk'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::maxsmc', group='CFE', description=opt_param_desc.format('CFE', 'maxsmc'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::slope', group='CFE', description=opt_param_desc.format('CFE', 'slope'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::b', group='CFE', description=opt_param_desc.format('CFE', 'b'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::multiplier', group='CFE', description=opt_param_desc.format('CFE', 'multiplier'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::Klf', group='CFE', description=opt_param_desc.format('CFE', 'Klf'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::Kn', group='CFE', description=opt_param_desc.format('CFE', 'Kn'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::Cgw', group='CFE', description=opt_param_desc.format('CFE', 'Cgw'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::expon', group='CFE', description=opt_param_desc.format('CFE', 'expon'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE']),
        FormulationParameter(name='CFE::max_gw_storage', group='CFE', description=opt_param_desc.format('CFE', 'max_gw_storage'), value_type='number', config_type='number', formulation=formulations['Multi::Noah_OWP::PET::CFE'])

    ])


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('MaaS', '0002_formulation_formulationparameter'),
    ]

    operations = [
        migrations.RunPython(create_premade_formulations)
    ]
