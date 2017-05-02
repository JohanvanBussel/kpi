from base_handlers import GroupHandler

from pprint import pprint

SPAN_WRAP = '<span style="display:none">{}</span>'
HEADER_WRAP = '**{}**'
ROW_HEADER_WRAP = '##### {}'


class KoboMatrixGroupHandler(GroupHandler):
    name = 'Kobo matrix group'

    start_type = 'begin_kobomatrix'
    end_type = 'end_kobomatrix'

    description = '''
    Allows a survey builder to create a table of different question types
    '''

    def __init__(self, base_handler):
        """
        Convert KoboScoreGroup:
        # survey
        |       type       | name | label | kobo--matrix_list | required |
        | ---------------- | ---- | ----- | ----------------- | -------- |
        | begin_kobomatrix | m1   |       | car_bike_tv       |          |
        | select_one yn    | q1   | Q1    |                   | true     |
        | text             | q2   | Q2    |                   | true     |
        | end_kobomatrix   |      |       |                   |          |

        # choices
        |  list name  | name | label |
        | ----------- | ---- | ----- |
        | yn          | yes  | Yes   |
        | yn          | no   | No    |
        | car_bike_tv | car  | Car   |
        | car_bike_tv | bike | Bike  |
        | car_bike_tv | tv   | TV    |

        into:

        # survey
        |      type     |      name      |   label    | appearance | required |
        | ------------- | -------------- | ---------- | ---------- | -------- |
        | begin_group   | m1_header      |            | w7         |          |
        | note          | m1_header_note | **Items**  | w1         | false    |
        | note          | m1_q1          | **Q1**     | w2         | false    |
        | note          | m1_q2          | **Q2**     | w2         | false    |
        | end_group     |                |            |            |          |
        | begin_group   | car            |            | w7         |          |
        | note          | car_note       | ##### Car  | w1         | false    |
        | select_one yn | car_q1         | **Q1**     | w2         | true     |
        | text          | car_q2         | **Q2**     | w2         | true     |
        | end_group     |                |            |            |          |
        | begin_group   | bike           |            | w7         |          |
        | note          | bike_note      | ##### Bike | w1         | false    |
        | select_one yn | bike_q1        | <s>Q1</s1> | w2         | true     |
        | text          | bike_q2        | <s>Q1</s1> | w2         | true     |
        | end_group     |                |            |            |          |
        | begin_group   | tv             |            | w7         |          |
        | note          | tv_note        | ##### TV   | w1         | false    |
        | select_one yn | tv_q1          | <s>Q1</s1> | w2         | true     |
        | text          | tv_q2          | <s>Q1</s1> | w2         | true     |
        | end_group     |                |            |            |          |

        # choices
        | list name   | name | label |
        |-------------|------|-------|
        | yn          | yes  | Yes   |
        | yn          | no   | No    |
        """
        self._base_handler = base_handler

    def begin(self, initial_row):
        super(KoboMatrixGroupHandler, self).begin(initial_row)

        choice_key = 'kobo--matrix_list'
        self.items = self._base_handler.choices(list_name=initial_row.pop(choice_key))
        self.item_labels = initial_row.get('label')
        self.span_wrap = initial_row.get('kobomatrix--span-wrap', SPAN_WRAP)
        self.header_wrap = initial_row.get('kobomatrix--header-wrap', HEADER_WRAP)
        self.row_header_wrap = initial_row.get('kobomatrix--row-header-wrap', ROW_HEADER_WRAP)
        self._rows = []

    def finish(self):
        survey_contents = self._base_handler.survey_contents

        for item in self._header(self.name, self.item_labels, self._rows):
            survey_contents.append(item)

        for item in self.items:
            for row in self._rows_for_item(self.name, item, self._rows):
                survey_contents.append(row)

    def _format_all_labels(self, labels, template):
        return [
            template.format(_l) for _l in labels
        ]

    def _header(self, name, items_label, cols):
        header_name = '_'.join([name, 'header'])
        start = [{'type': 'begin_group',
                  'name': header_name,
                  'appearance': 'w7',
                  },
                 {'type': 'note',
                  'name': '{}_note'.format(header_name),
                  'appearance': 'w1',
                  'required': False,
                  'label': self._format_all_labels(items_label, self.header_wrap),
                  }]

        mids = [
            {'type': 'note',
             'appearance': 'w2',
             'required': False,
             'label': self._format_all_labels(col.get('label'), self.header_wrap),
             'name': '_'.join([header_name, col.get('name')])
             }
            for col in cols
        ]
        return start + mids + [{'type': 'end_group'}]

    def _rows_for_item(self, name, item, cols):
        _item_name = item.get('name')
        _base_name = '_'.join([name, _item_name])
        start = [{'type': 'begin_group',
                  'name': _base_name,
                  'appearance': 'w7',
                  },
                 {'type': 'note',
                  'name': '{}_note'.format(_base_name),
                  'label': self._format_all_labels(item.get('label'),
                                                   self.row_header_wrap),
                  'required': False,
                  'appearance': 'w1',
                  }]

        def _make_row(col):
            _type = col['type']
            _appearance = ['w2']
            if _type in ['select_one', 'select_multiple']:
                _appearance.append('horizontal-compact')
            else:
                _appearance.append('no-label')
            out = {'type': _type,
                   'name': '_'.join([_base_name, col['name']]),
                   'appearance': ' '.join(_appearance),
                   'label': self._format_all_labels([
                       '-'.join([_item_name, _label])
                       for _label in col.get('label')
                   ], self.span_wrap),
                   'required': col.get('required', False),
                   }
            if 'select_from_list_name' in col:
                out['select_from_list_name'] = col['select_from_list_name']
            return out

        return start + [_make_row(col) for col in cols] + [{'type': 'end_group'}]

    def handle_row(self, row):
        if row.get('type') == self.end_type:
            self.finish()
            return False
        else:
            self._rows.append(row)
            return self