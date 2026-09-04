from glob import glob

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QWidget, QHBoxLayout, QSizePolicy, QApplication

from bauh import __version__, ROOT_DIR
from bauh.context import generate_i18n
from bauh.view.util import resource

# repositorio de este fork
PROJECT_URL = 'https://github.com/The-Gekko/The-Gekko-Bauh'
# repositorio original del que deriva el fork
UPSTREAM_URL = 'https://github.com/vinifmor/bauh'
UPSTREAM_LABEL = 'vinifmor/bauh'
LICENSE_URL = 'https://raw.githubusercontent.com/The-Gekko/The-Gekko-Bauh/master/LICENSE'


def get_display_name() -> str:
    """Devuelve el nombre visible del fork.

    El import es diferido porque 'bauh.view.qt.window' expone ManageWindow, que a su vez
    depende de este modulo: importarlo arriba crearia un ciclo.
    """
    from bauh.view.qt.window.constants import DISPLAY_NAME
    return DISPLAY_NAME


class AboutDialog(QDialog):

    def __init__(self, app_config: dict):
        super(AboutDialog, self).__init__()
        display_name = get_display_name()
        i18n = generate_i18n(app_config, resource.get_path('locale/about'))
        self.setWindowTitle('{} ({})'.format(i18n['about.title'].capitalize(), display_name))
        layout = QVBoxLayout()
        self.setLayout(layout)

        logo_container = QWidget()
        logo_container.setObjectName('logo_container')
        logo_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        logo_container.setLayout(QHBoxLayout())

        label_logo = QLabel()
        label_logo.setObjectName('logo')

        logo_container.layout().addWidget(label_logo)
        layout.addWidget(logo_container)

        label_name = QLabel(display_name)
        label_name.setObjectName('app_name')
        layout.addWidget(label_name)

        label_version = QLabel(i18n['about.version'].lower() + ' ' + __version__)
        label_version.setObjectName('app_version')
        layout.addWidget(label_version)

        layout.addWidget(QLabel(''))

        line_desc = QLabel(i18n['about.info.desc'])
        line_desc.setObjectName('app_description')
        layout.addWidget(line_desc)

        layout.addWidget(QLabel(''))

        available_gems = [f for f in glob('{}/gems/*'.format(ROOT_DIR)) if not f.endswith('.py') and not f.endswith('__pycache__')]
        available_gems.sort()

        gems_widget = QWidget()
        gems_widget.setLayout(QHBoxLayout())

        gems_widget.layout().addWidget(QLabel())
        gem_logo_size = int(0.032552083 * QApplication.primaryScreen().size().height())

        for gem_path in available_gems:
            icon = QLabel()
            icon.setObjectName('gem_logo')
            icon_path = gem_path + '/resources/img/{}.svg'.format(gem_path.split('/')[-1])
            icon.setPixmap(QIcon(icon_path).pixmap(gem_logo_size, gem_logo_size))
            gems_widget.layout().addWidget(icon)

        gems_widget.layout().addWidget(QLabel())

        layout.addWidget(gems_widget)
        layout.addWidget(QLabel(''))

        # la licencia zlib exige marcar claramente las versiones alteradas: se indica el origen del fork
        label_fork = QLabel()
        label_fork.setObjectName('app_fork')
        label_fork.setText(i18n['about.info.fork'].format(f"<a href='{UPSTREAM_URL}'>{UPSTREAM_LABEL}</a>"))
        label_fork.setOpenExternalLinks(True)
        layout.addWidget(label_fork)

        label_more_info = QLabel()
        label_more_info.setObjectName('app_more_information')
        label_more_info.setText(i18n['about.info.link'] + " <a href='{url}'>{url}</a>".format(url=PROJECT_URL))
        label_more_info.setOpenExternalLinks(True)
        layout.addWidget(label_more_info)

        label_license = QLabel()
        label_license.setObjectName('app_license')
        label_license.setText("<a href='{}'>{}</a>".format(LICENSE_URL, i18n['about.info.license']))
        label_license.setOpenExternalLinks(True)
        layout.addWidget(label_license)

        layout.addWidget(QLabel(''))

        label_trouble_question = QLabel(i18n['about.info.trouble.question'])
        label_trouble_question.setObjectName('app_trouble_question')

        layout.addWidget(label_trouble_question)

        label_trouble_answer = QLabel(i18n['about.info.trouble.answer'])
        label_trouble_answer.setObjectName('app_trouble_answer')

        layout.addWidget(label_trouble_answer)

        layout.addWidget(QLabel(''))

        label_rate_question = QLabel(i18n['about.info.rate.question'])
        label_rate_question.setObjectName('app_rate_question')
        layout.addWidget(label_rate_question)

        label_rate_answer = QLabel(i18n['about.info.rate.answer'])
        label_rate_answer.setObjectName('app_rate_answer')
        layout.addWidget(label_rate_answer)

        layout.addWidget(QLabel(''))

        self.adjustSize()
        self.setFixedSize(self.size())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
