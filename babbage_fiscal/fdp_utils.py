from normality import slugify

from .db_utils import database_name


def fdp_to_model(package, table_name, resource, field_translator):
    """
    Create a Babbage Model from a Fiscal DataPackage descriptor
    :param package: datapackage object
    :param table_name: db table name to use
    :param resource: resource to load (in the datapackage object)
    :param field_translator: dict for translating resource attribute names to valid db column names
    :return: Babbage Model
    """
    model = {
        'fact_table': table_name,
        'measures': {},
        'dimensions': {}
    }

    mapping = package.metadata['mapping']
    resource_name = resource.metadata['name']

    # Converting measures
    all_measures = set()
    for orig_name, measure in mapping['measures'].items():
        if resource_name != measure.get('resource', resource_name):
            continue
        name = database_name(orig_name, all_measures, 'measure')
        all_measures.add(name)
        babbage_measure = {
            'label': orig_name,
            'column': field_translator[measure['source']]['name'],
            'orig_measure': orig_name
        }
        if 'currency' in measure:
            babbage_measure['currency'] = measure['currency']
        model['measures'][name]=babbage_measure

    hierarchies = {}

    # Converting dimensions
    all_dimensions = set()
    for orig_name,dimension in mapping['dimensions'].items():
        name = database_name(orig_name, all_dimensions, 'dimension')
        all_dimensions.add(name)
        attributes = dimension['attributes']
        primaryKeys = dimension['primaryKey']
        if not isinstance(primaryKeys,list):
            primaryKeys = [primaryKeys]
        # Marking which attributes have labels
        labels = {}
        for label_name, attr in attributes.items():
            if 'labelfor' in attr:
                labels[attr['labelfor']] = label_name
        # Flattening multi-key dimensions into separate dimensions
        for pkey in primaryKeys:
            if len(primaryKeys) > 1:
                label = name + '.' + pkey
                dimname = name + '_' + pkey
            else:
                label = name
                dimname = name
            translated_field = field_translator[attributes[pkey]['source']]
            source = translated_field['name']
            type = translated_field['type']
            babbage_dimension = {
                'attributes': {
                    pkey: {'column': source, 'label': pkey,
                           'datatype': type, 'orig_attribute': pkey}
                },
                'label': label,
                'key_attribute': pkey,
                'orig_dimension': orig_name
            }
            hierarchies.setdefault(name, {'levels': []})['levels'].append(dimname)
            if pkey in labels:
                label = labels[pkey]
                translated_label_field = field_translator[attributes[label]['source']]
                label_source = translated_label_field['name']
                label_type = translated_label_field['type']
                babbage_dimension['attributes'][label] = {
                    'column': label_source, 'label': label,
                    'datatype': label_type, 'orig_attribute': label
                }
                babbage_dimension['label_attribute'] = label_source
            if len(primaryKeys) == 1:
                # Copy other attributes as well
                for attr_name, attr in attributes.items():
                    if attr_name not in (pkey, labels.get(pkey)):
                        translated_attr_field = field_translator[attributes[attr_name]['source']]
                        attr_source = translated_attr_field['name']
                        attr_type = translated_attr_field['type']
                        babbage_dimension['attributes'][attr_name] = {
                            'column': attr_source, 'label': attr_name,
                            'datatype': attr_type, 'orig_attribute': attr_name
                        }

            model['dimensions'][dimname] = babbage_dimension
        model['hierarchies'] = dict((k,v) for k,v in hierarchies.items() if len(v['levels']) > 1)

    return model
