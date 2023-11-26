import sys

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QCheckBox, QPushButton,
                               QScrollArea, QGroupBox, QApplication, QLabel, QMainWindow)

from PySide6.QtCore import QFile, QTextStream, Signal
from PySide6.QtGui import QIcon

from src.frontend.ui_form import Ui_Porn_Fetch_Widget
from src.frontend import ressources_rc
from phub import locals

categories = [attr for attr in dir(locals.Category) if
              not callable(getattr(locals.Category, attr)) and not attr.startswith("__")]


class CategoryFilterWindow(QWidget):
    data_selected = Signal((str, list))

    def __init__(self, categories):
        super().__init__()
        self.radio_buttons = {}
        self.checkboxes = {}
        self.categories = categories

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        left_layout = QVBoxLayout()
        left_group = QGroupBox("Select Category")

        for category in self.categories:
            radio_button = QRadioButton(category)
            left_layout.addWidget(radio_button)
            self.radio_buttons[category] = radio_button

        left_group.setLayout(left_layout)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_group)

        right_layout = QVBoxLayout()
        right_group = QGroupBox("Exclude Categories")

        for category in self.categories:
            checkbox = QCheckBox(category)
            right_layout.addWidget(checkbox)
            self.checkboxes[category] = checkbox

        right_group.setLayout(right_layout)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_group)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.on_apply)

        hlayout = QHBoxLayout()
        hlayout.addWidget(left_scroll)
        hlayout.addWidget(right_scroll)

        layout.addLayout(hlayout)
        layout.addWidget(apply_button)
        self.setLayout(layout)

    def on_apply(self):
        selected_category = None
        excluded_categories = []

        for category, radio_button in self.radio_buttons.items():
            if radio_button.isChecked():
                selected_category = category

        for category, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                excluded_categories.append(category)

        # Instead of writing to a file, emit a signal or return the values
        self.selected_category = selected_category
        self.excluded_categories = excluded_categories
        self.data_selected.emit(self.selected_category, self.excluded_categories)
        self.close()


class PornFetch(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_category = None
        self.excluded_categories_filter = None
        self.ui = Ui_Porn_Fetch_Widget()
        self.ui.setupUi(self)
        self.button_connectors()
        self.load_icons()


    def load_icons(self):
        self.ui.button_switch_search.setIcon(QIcon(":/images/graphics/search.svg"))
        self.ui.button_switch_home.setIcon(QIcon(":/images/graphics/download.svg"))
        self.ui.button_switch_settings.setIcon(QIcon(":/images/graphics/settings.svg"))
        self.ui.button_switch_credits.setIcon(QIcon(":/images/graphics/information.svg"))


    def button_connectors(self):
        """a function to link the buttons to their functions"""

        self.ui.button_switch_home.clicked.connect(self.switch_to_home)
        self.ui.button_switch_search.clicked.connect(self.switch_to_search)


    def switch_to_home(self):
        print("Changed Index to 0")
        self.ui.stacked_widget_top.setCurrentIndex(0)

    def switch_to_search(self):
        print("Changed Index to 1")
        self.ui.stacked_widget_top.setCurrentIndex(1)





    def handle_selected_data(self, selected_category, excluded_categories):
        self.selected_category = selected_category
        self.excluded_categories_filter = excluded_categories

    def search_videos(self):
        include_filters = []
        exclude_filters = []

        filter_objects = {
            'include': [self.selected_category],
            'exclude': [self.excluded_categories_filter]
        }

        for action, filters in filter_objects.items():
            for filter_object in filters:
                if isinstance(filter_object, locals.Param):
                    if action == 'include':
                        include_filters.append(filter_object)
                    elif action == 'exclude':
                        exclude_filters.append(filter_object)
                else:
                    print(f"Invalid filter")

        if include_filters:
            combined_include_filter = include_filters[0]
            for filter_object in include_filters[1:]:
                combined_include_filter |= filter_object
        else:
            combined_include_filter = None

        if exclude_filters:
            combined_exclude_filter = exclude_filters[0]
            for filter_object in exclude_filters[1:]:
                combined_exclude_filter -= filter_object
        else:
            combined_exclude_filter = None

        query = self.ui.lineedit_search_query.text()

        if combined_include_filter and combined_exclude_filter:
            final_filter = combined_include_filter - combined_exclude_filter
            query_object = self.client.search(query, final_filter)
        elif combined_include_filter:
            query_object = self.client.search(query, combined_include_filter)
        elif combined_exclude_filter:
            query_object = self.client.search(query, -combined_exclude_filter)
        else:
            query_object = self.client.search(query)

        for video in query_object:
            print(video.title)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file = QFile(":/style/stylesheet.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())


    widget = PornFetch()
    widget.show()
    sys.exit(app.exec())
