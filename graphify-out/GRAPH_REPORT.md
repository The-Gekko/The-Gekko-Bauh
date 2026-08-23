# Graph Report - Bauh Fork The-Gekko  (2026-08-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3381 nodes · 10395 edges · 185 communities (137 shown, 48 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1024 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1e50b94`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PackageView
- I18n
- AsyncAction
- FlatpakApplication
- HttpClient
- get_human_size_str
- SoftwarePackage
- AsyncAction
- SoftwareManager
- CustomSoftwareAction
- ArchPackage
- manage_window.py
- FormComponent
- ManageWindow
- ArchManager
- ProcessWatcher
- pacman.py
- view.py
- WindowActionsMixin
- GenericSoftwareManager
- SettingsWindow
- FormQt
- TransactionContext
- UpgradeRequirement
- QtComponentsManager
- bauh/context.py
- GitHubManager
- debian/controller.py
- SimpleProcess
- InputOption
- MemoryCache
- DebianPackageManager
- ApplicationContext
- arch/controller.py
- get_icon_path
- Aptitude
- DebianPackage
- CategoriesDownloader
- PreparePanel
- AppImage
- UpdatesSummarizer
- WebApplicationManager
- WebApplication
- AdaptableFileDownloader
- threads/util.py
- components.py
- EopkgPackage
- rebuild_detector.py
- flatpak.py
- GitHubPackage
- WindowUIMixin
- PackagesTable
- TaskManager
- AURClient
- AppImageManager
- EnvironmentUpdater
- DiskCacheLoader
- DependenciesAnalyser
- AsyncAction
- system.py
- replace_desktop_entry_exec_command
- SearchResult
- aptitude.py
- SynchronizePackages
- SnapManager
- PackageUpdate
- web/worker.py
- AURDataMapper
- install.sh
- FlatpakManager
- SortingTest
- manage.py
- match_required_version
- DebianSuggestionsDownloader
- systray.py
- AnimateProgress
- WebApplicationManagerTest
- CoreConfigManager
- TransactionStatusHandler
- ._uninstall
- snapd.py
- AptitudeTest
- FlatpakManagerSortUpdateOrderTest
- AnimateProgress
- RepositorySuggestionsDownloader
- AsyncDiskCacheLoader
- AppImageSuggestionsDownloader
- .__init__
- PacmanTest
- NullLoggerFactory
- SuggestionsManager
- ScreenshotsDialog
- AURModuleTest
- StylesheetTest
- TabGroupComponent
- GitHubConfigManager
- write_as_user
- .__init__
- ArchDiskCacheUpdater
- DebianPackageManagerTest
- ConfigManager
- Value
- ArchCompilationOptimizer
- DebianViewBridge
- strip_html
- .read_installed
- get_icon_path
- AnimateProgress
- AnimateProgress
- DatabaseUpdater
- arch/disk.py
- .__init__
- AnyInstance
- CoreConfigManagerTest
- GemsLoaderTest
- commons/config.py
- AppImageConfigManager
- DebianConfigManager
- EopkgConfigManager
- YAMLConfigManager
- SnapConfigManager
- WebConfigManager
- Singleton
- pkgbuild.py
- build.sh

## God Nodes (most connected - your core abstractions)
1. `I18n` - 333 edges
2. `SoftwareManager` - 251 edges
3. `PackageView` - 217 edges
4. `SoftwarePackage` - 200 edges
5. `ProcessWatcher` - 196 edges
6. `ArchManager` - 168 edges
7. `ArchPackage` - 139 edges
8. `ProcessHandler` - 125 edges
9. `bold()` - 124 edges
10. `SimpleProcess` - 105 edges

## Surprising Connections (you probably didn't know these)
- `TestPackageView` --uses--> `PackageView`  [INFERRED]
  tests/view/qt/test_view_model.py → bauh/view/qt/view_model.py
- `DebianPackageManagerTest` --uses--> `SearchResult`  [INFERRED]
  tests/gems/debian/test_controller.py → bauh/api/abstract/controller.py
- `TestPackageView` --uses--> `SoftwarePackage`  [INFERRED]
  tests/view/qt/test_view_model.py → bauh/api/abstract/model.py
- `CoreConfigManagerTest` --uses--> `YAMLConfigManager`  [INFERRED]
  tests/view/core/test_config.py → bauh/commons/config.py
- `TestManageWindow` --uses--> `MemoryCache`  [INFERRED]
  tests/view/qt/test_manage_window.py → bauh/api/abstract/cache.py

## Import Cycles
- None detected.

## Communities (185 total, 48 thin omitted)

### Community 0 - "PackageView"
Cohesion: 0.04
Nodes (24): ApplyFilters, DowngradePackage, InstallPackage, LaunchPackage, ListWarnings, NotifyInstalledLoaded, NotifyPackagesReady, Logger (+16 more)

### Community 1 - "I18n"
Cohesion: 0.06
Nodes (17): Logger, ApplyFilters, FindSuggestions, IgnorePackageUpdates, LaunchPackage, ListWarnings, Logger, QObject (+9 more)

### Community 2 - "AsyncAction"
Cohesion: 0.07
Nodes (11): ApplyFilters, AsyncAction, CustomAction, DowngradePackage, FindSuggestions, IgnorePackageUpdates, LaunchPackage, RefreshApps (+3 more)

### Community 4 - "HttpClient"
Cohesion: 0.06
Nodes (23): Logger, :param download_icons: if packages icons should be downloaded :param…, FileDownloader, ABC, :param file_url: :param watcher: :param output_path: the downloaded file output…, HttpClient, Logger, Response (+15 more)

### Community 5 - "get_human_size_str"
Cohesion: 0.06
Nodes (7): get_human_size_str(), AsyncAction, UpgradeSelected, AsyncAction, UpgradeSelected, GetHumanSizeStrTest, TestCase

### Community 6 - "SoftwarePackage"
Cohesion: 0.03
Nodes (29): return additional required software that needs to be installed / removed /…, :param pkg: :return:, Saves the package data to the hard disk. :param pkg: :param icon_bytes: :param…, Sames as above, but does not check if disk cache is enabled or supported by the…, if a given action requires root privileges to be executed. 'install',…, At the moment the GUI implements this action. No need to implement it yourself.…, PackageHistory, ABC (+21 more)

### Community 7 - "AsyncAction"
Cohesion: 0.05
Nodes (16): ApplyFilters, AsyncAction, DowngradePackage, FindSuggestions, IgnorePackageUpdates, InstallPackage, LaunchPackage, Logger (+8 more)

### Community 8 - "SoftwareManager"
Cohesion: 0.03
Nodes (33): Base controller class that will be called by the graphical interface to execute…, downgrades a package version :param pkg: :param root_password: the root user…, Cleans cached package cached data. This default implementation only cleans the…, :param requirements: :param root_password: the root user password (if required)…, :return: the managed package class type, retrieve the package information :param pkg: :return: a dictionary with the…, :return: if the instance is enabled, :param enabled: :return: (+25 more)

### Community 9 - "CustomSoftwareAction"
Cohesion: 0.11
Nodes (13): ABC, Enum, SettingsController, SoftwareAction, UpgradeRequirements, CustomSoftwareAction, PackageSuggestion, Enum (+5 more)

### Community 11 - "manage_window.py"
Cohesion: 0.15
Nodes (16): notify_tray(), sum_updates_displayed(), new_spacer(), IconButton, QToolButton, QCustomToolbar, HistoryDialog, QDialog (+8 more)

### Community 12 - "FormComponent"
Cohesion: 0.13
Nodes (10): SettingsView, FileChooserComponent, FormComponent, PanelComponent, TabComponent, TextInputComponent, new_select(), ManualInstallationFileObserver (+2 more)

### Community 13 - "ManageWindow"
Cohesion: 0.06
Nodes (6): ManageWindow, QCloseEvent, QShowEvent, WindowFiltersMixin, QEvent, TestManageWindow

### Community 14 - "ArchManager"
Cohesion: 0.07
Nodes (4): ArchManager, Any, datetime, Thread

### Community 15 - "ProcessWatcher"
Cohesion: 0.06
Nodes (17): ProcessWatcher, prints a given message to the user. In the current GUI implementation, the…, request a user confirmation. In the current GUI implementation, it shows a…, :return: requests a system reboot, Changes the process status. In the current GUI implementation, the process…, Changes the process substatus. In the current GUI implementation, the process…, Represents an view component watching background processes. It's a bridge for…, Changes the process progress. In the current GUI implementation, the progress… (+9 more)

### Community 16 - "pacman.py"
Cohesion: 0.07
Nodes (47): runs a given command and returns its default output :return:, run(), run_cmd(), can_refresh_mirrors(), check_installed(), fill_ignored_packages(), _fill_provided_map(), find_one_match() (+39 more)

### Community 17 - "view.py"
Cohesion: 0.14
Nodes (12): :return: a tuple with a bool informing if the settings were saved and a list of…, Enum, Represents a GUI component, SelectViewType, SpacerComponent, TextComponent, TextInputType, TwoStateButtonComponent (+4 more)

### Community 20 - "SettingsWindow"
Cohesion: 0.16
Nodes (5): QShowEvent, QThread, QWidget, ReloadManagePanel, SettingsWindow

### Community 21 - "FormQt"
Cohesion: 0.09
Nodes (16): AlignmentFlag, ColorPickerComponent, InputViewComponent, RangeInputComponent, Represents a component which needs a user interaction to provide its value, ColorPickerQt, FormComboBoxQt, FormQt (+8 more)

### Community 23 - "UpgradeRequirement"
Cohesion: 0.13
Nodes (13): :param pkg: :param reason: :param required_size: size in BYTES required to…, :param to_install: additional packages that must be installed with the upgrade…, UpgradeRequirement, patch, TestCase, If the newest version o package A conflicts with itself, then A should not be…, If the newest version o package A conflicts with a provided package C (by…, Scenario: - Package V (2.5.0)[update] -> conflicts: X<21.1.1, X-ABI-… (+5 more)

### Community 24 - "QtComponentsManager"
Cohesion: 0.13
Nodes (3): QWidget, QtComponentsManager, QAction

### Community 25 - "bauh/context.py"
Cohesion: 0.12
Nodes (22): new_qt_application(), Logger, QApplication, set_theme(), setup_theme_watcher(), _by_str_len(), parse_gtk_matugen_colors(), process_theme() (+14 more)

### Community 26 - "GitHubManager"
Cohesion: 0.08
Nodes (14): BuildMethod, detect_build_method(), Enum, Analyzes the root directory of a cloned repository and returns the detected…, Returns True if the build method requires root/sudo to install., requires_root(), GitHubManager, Scans the repos directory for cloned repositories. (+6 more)

### Community 27 - "debian/controller.py"
Cohesion: 0.09
Nodes (11): ApplicationIndexer, ApplicationIndexError, ApplicationsMapper, Exception, Logger, DebianApplication, For packages that represent applications, ApplicationIndexerTest (+3 more)

### Community 28 - "SimpleProcess"
Cohesion: 0.07
Nodes (28): SimpleProcess, is_supported(), clone(), is_installed(), build(), check(), gen_srcinfo(), list_output_files() (+20 more)

### Community 29 - "InputOption"
Cohesion: 0.11
Nodes (18): InputOption, MultipleSelectComponent, Represents a select component option., :param label: the string that will be shown to the user :param value: the…, SingleSelectComponent, get_path(), confirm_missing_deps(), _get_repo_icon() (+10 more)

### Community 30 - "MemoryCache"
Cohesion: 0.07
Nodes (16): MemoryCache, MemoryCacheFactory, ABC, Instantiate new memory cache instances., :param expiration: expiration time for the cache keys in seconds. Use -1 to…, Represents a memory cache., InfoDialog, QDialog (+8 more)

### Community 32 - "ApplicationContext"
Cohesion: 0.07
Nodes (10): ApplicationContext, FlatpakAsyncDataLoader, Thread, CheckFinished, EnableSkip, Prepare, QThread, QTableWidget (+2 more)

### Community 33 - "arch/controller.py"
Cohesion: 0.10
Nodes (18): parse(), Logger, sort_by_priority(), # TODO: multi-threaded download client cannot be run as another user at the…, Logger, register_sync(), should_sync(), PackageInHoldException (+10 more)

### Community 34 - "get_icon_path"
Cohesion: 0.14
Nodes (8): get_temp_dir(), get_icon_path(), get_pkgbuild_dir(), AURIndexUpdater, Logger, Thread, RefreshMirrors, SyncDatabases

### Community 35 - "Aptitude"
Cohesion: 0.10
Nodes (5): Aptitude, Collection, Logger, Pattern, DebianTransaction

### Community 36 - "DebianPackage"
Cohesion: 0.07
Nodes (5): fill_show_data(), strip_maintainer_email(), strip_section(), DebianPackage, Collection

### Community 37 - "CategoriesDownloader"
Cohesion: 0.09
Nodes (15): CategoriesDownloader, Logger, Thread, :param id_: :param http_client: :param logger: :param manager: :param…, datetime_as_milis(), map_timestamp_file(), datetime, sanitize_command_input() (+7 more)

### Community 38 - "PreparePanel"
Cohesion: 0.08
Nodes (10): PreparePanel, QCloseEvent, QShowEvent, QWidget, QDialog, QThread, QWidget, RootDialog (+2 more)

### Community 40 - "UpdatesSummarizer"
Cohesion: 0.18
Nodes (5): Any, Parameters pkgs_data: a dict mapping the packages whose conflicts need to be…, Parameters context: update context install_data: a dict mapping the packages to…, UpdateRequirementsContext, UpdatesSummarizer

### Community 44 - "threads/util.py"
Cohesion: 0.07
Nodes (43): shows a message to the user. In the current GUI implementation, it shows a…, PackageStatus, :param id: :param version: :param name: :param description: :param…, MessageType, NoInternetException, Exception, InternetChecker, get_app_commits_data() (+35 more)

### Community 45 - "components.py"
Cohesion: 0.10
Nodes (22): Alignment, new_single_select(), QWidget, to_widget(), TwoStateButtonQt, ComboSelectQt, QGroupBox, QCustomLineEdit (+14 more)

### Community 47 - "rebuild_detector.py"
Cohesion: 0.47
Nodes (4): add_as_ignored(), list_ignored(), list_required_rebuild(), remove_from_ignored()

### Community 48 - "flatpak.py"
Cohesion: 0.09
Nodes (23): map_str_version(), downgrade(), fill_updates(), full_update(), get_app_commits(), get_app_info(), get_app_info_fields(), get_commit() (+15 more)

### Community 50 - "WindowUIMixin"
Cohesion: 0.08
Nodes (8): QIcon, QWidget, QCustomMenuAction, QCheckBox, QWidget, WindowUIMixin, QMenu, QWidgetAction

### Community 51 - "PackagesTable"
Cohesion: 0.09
Nodes (12): PackagesTable, Logger, QIcon, QLabel, QSize, QToolButton, QWidget, UpgradeToggleButton (+4 more)

### Community 52 - "TaskManager"
Cohesion: 0.10
Nodes (11): It prepares the manager to start working. It will be called by GUI. Do not call…, :param task_id: :param progress: a float between 0 and 100. :param substatus:…, updates the task output :param task_id: :param output: :return:, marks a task as finished :param task_id: :return:, :param id_: an unique identifier for the task :param label: an i18n label…, TaskManager, CreateConfigFile, Logger (+3 more)

### Community 53 - "AURClient"
Cohesion: 0.15
Nodes (5): AURClient, map_srcinfo(), merge_subinfos(), Logger, Logger

### Community 56 - "DiskCacheLoader"
Cohesion: 0.15
Nodes (9): The result of a given operation, :param pkg: :param root_password: the root user password (if required) :param…, TransactionResult, DiskCacheLoader, Any, maps a given cache instance for a given package type :param cache: :param…, fill cached data from the disk of a given package instance If a cache mapping…, returns the cached data from the given package (+1 more)

### Community 57 - "DependenciesAnalyser"
Cohesion: 0.13
Nodes (7): DependenciesAnalyser, map_providers(), Pattern, fills the missing data of the single dependency providers since they are…, :param missing_deps: :param provided_map: :param remote_repo_map: :param…, :param names: :param repository: :param in_analysis: global set storing all…, Logger

### Community 59 - "system.py"
Cohesion: 0.07
Nodes (32): check_active_services(), check_enabled_services(), execute(), gen_env(), new_root_subprocess(), new_subprocess(), Any, Popen (+24 more)

### Community 60 - "replace_desktop_entry_exec_command"
Cohesion: 0.18
Nodes (3): replace_desktop_entry_exec_command(), TestCase, TestUtil

### Community 61 - "SearchResult"
Cohesion: 0.08
Nodes (7): :param words: the words typed by the user :param disk_loader: a running disk…, :param disk_loader: a running disk loader thread that loads application data…, :param installed: already installed packages :param new: new packages found…, SearchResult, EopkgManager, Executes an eopkg command and returns (success, output)., P

### Community 62 - "aptitude.py"
Cohesion: 0.12
Nodes (9): StringIO, AptitudeAction, AptitudeOutputHandler, AptitudeOutputHandlerFactory, map_package_name(), Enum, Thread, MapPackageNameTest (+1 more)

### Community 63 - "SynchronizePackages"
Cohesion: 0.18
Nodes (5): MapApplications, Logger, Thread, SynchronizePackages, UpdateApplicationIndex

### Community 64 - "SnapManager"
Cohesion: 0.06
Nodes (3): SnapManager, SnapApplication, SnapdClient

### Community 65 - "PackageUpdate"
Cohesion: 0.19
Nodes (4): PackageUpdate, :param pkg_id: an unique package identifier :param version: the new version…, PackageUpdateTest, TestCase

### Community 66 - "web/worker.py"
Cohesion: 0.17
Nodes (8): get_icon_path(), Logger, SearchIndexManager, Logger, Thread, SearchIndexGenerator, SuggestionsLoader, UpdateEnvironmentSettings

### Community 67 - "AURDataMapper"
Cohesion: 0.12
Nodes (3): AURDataMapper, ArchDataMapperTest, TestCase

### Community 68 - "install.sh"
Cohesion: 0.26
Nodes (12): check_chaotic_aur(), ensure_pipx(), error(), handle_original_bauh(), info(), install_icon_and_desktop(), install_main(), refresh_desktop_caches() (+4 more)

### Community 70 - "SortingTest"
Cohesion: 0.13
Nodes (6): TestCase, dep order: abc -> ghi jkl -> ghi ghi -> def def -> mno expected: def, ghi, (abc…, dep order: abc -> def -> ghi -> jkl -> abc, dep order: abc -> fed def (fed) ghi -> abc expected: def, abc, ghi, dep order = abc -> ghi -> def expected: def, ghi, abc, SortingTest

### Community 71 - "manage.py"
Cohesion: 0.07
Nodes (33): is_root(), Namespace, read(), main(), qt_message_handler(), tray(), main(), Namespace (+25 more)

### Community 72 - "match_required_version"
Cohesion: 0.29
Nodes (3): match_required_version(), MatchRequiredVersionTest, TestCase

### Community 73 - "DebianSuggestionsDownloader"
Cohesion: 0.25
Nodes (3): DebianSuggestionsDownloader, Logger, Thread

### Community 74 - "systray.py"
Cohesion: 0.08
Nodes (18): AboutDialog, QDialog, load_icon(), load_resource_icon(), QIcon, AppUpdateCheck, get_cli_path(), list_updates() (+10 more)

### Community 75 - "AnimateProgress"
Cohesion: 0.08
Nodes (8): AnimateProgress, ListWarnings, NotifyInstalledLoaded, NotifyPackagesReady, QThread, QWidget, SaveTheme, StartAsyncAction

### Community 76 - "WebApplicationManagerTest"
Cohesion: 0.17
Nodes (4): ControllerTest, patch, TestCase, WebApplicationManagerTest

### Community 77 - "CoreConfigManager"
Cohesion: 0.12
Nodes (4): CoreConfigManager, InstallPackage, DowngradePackage, UninstallPackage

### Community 78 - "TransactionStatusHandler"
Cohesion: 0.20
Nodes (4): Collection, Logger, Thread, TransactionStatusHandler

### Community 80 - "snapd.py"
Cohesion: 0.15
Nodes (9): is_running(), Logger, SnapdAdapter, SnapdConnection, SnapdConnectionPool, HTTPAdapter, HTTPConnection, HTTPConnectionPool (+1 more)

### Community 85 - "AsyncDiskCacheLoader"
Cohesion: 0.15
Nodes (7): DiskCacheLoaderFactory, ABC, Associated a cache instance to instances of a given SoftwarePackage class…, AsyncDiskCacheLoader, Any, Thread, Adds a package which data must be read from the disk to a queue (if not sync)…

### Community 87 - ".__init__"
Cohesion: 0.06
Nodes (11): AnimateProgress, ListWarnings, NotifyInstalledLoaded, NotifyPackagesReady, Logger, QObject, QThread, QWidget (+3 more)

### Community 88 - "PacmanTest"
Cohesion: 0.23
Nodes (3): PacmanTest, patch, TestCase

### Community 89 - "NullLoggerFactory"
Cohesion: 0.40
Nodes (3): NullLoggerFactory, ABC, Logger

### Community 95 - "TabGroupComponent"
Cohesion: 0.19
Nodes (5): ABC, Represents a GUI component composed by other components, TabGroupComponent, ViewContainer, V

### Community 97 - "write_as_user"
Cohesion: 0.31
Nodes (5): CallAsUser, exec_as_user(), write_as_user(), WriteToFile, R

### Community 100 - "DebianPackageManagerTest"
Cohesion: 0.36
Nodes (3): DebianPackageManagerTest, patch, TestCase

### Community 110 - "AnimateProgress"
Cohesion: 0.11
Nodes (6): AnimateProgress, NotifyInstalledLoaded, NotifyPackagesReady, QThread, SaveTheme, StartAsyncAction

### Community 113 - "DatabaseUpdater"
Cohesion: 0.21
Nodes (4): get_icon_path(), DatabaseUpdater, Logger, SymlinksVerifier

### Community 114 - "arch/disk.py"
Cohesion: 0.53
Nodes (5): find_best_desktop_entry(), read_desktop_exec_and_icon(), write(), write_several(), callable

### Community 115 - ".__init__"
Cohesion: 0.53
Nodes (5): ask_confirmation(), _default_icon(), QIcon, QWidget, show_message()

### Community 117 - "CoreConfigManagerTest"
Cohesion: 0.33
Nodes (3): CoreConfigManagerTest, object, TestCase

### Community 118 - "GemsLoaderTest"
Cohesion: 0.40
Nodes (3): GemsLoaderTest, object, TestCase

## Knowledge Gaps
- **1 isolated node(s):** `build.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `I18n` connect `I18n` to `PackageView`, `AsyncAction`, `FlatpakApplication`, `HttpClient`, `get_human_size_str`, `SoftwarePackage`, `AsyncAction`, `SoftwareManager`, `CustomSoftwareAction`, `ArchPackage`, `manage_window.py`, `ManageWindow`, `ProcessWatcher`, `view.py`, `SettingsWindow`, `FormQt`, `UpgradeRequirement`, `bauh/context.py`, `debian/controller.py`, `InputOption`, `MemoryCache`, `ApplicationContext`, `arch/controller.py`, `get_icon_path`, `CategoriesDownloader`, `PreparePanel`, `AppImage`, `UpdatesSummarizer`, `AdaptableFileDownloader`, `threads/util.py`, `components.py`, `PackagesTable`, `TaskManager`, `AURClient`, `EnvironmentUpdater`, `DependenciesAnalyser`, `AsyncAction`, `aptitude.py`, `SynchronizePackages`, `web/worker.py`, `AURDataMapper`, `manage.py`, `DebianSuggestionsDownloader`, `systray.py`, `AnimateProgress`, `CoreConfigManager`, `TransactionStatusHandler`, `RepositorySuggestionsDownloader`, `AppImageSuggestionsDownloader`, `.__init__`, `SuggestionsManager`, `ScreenshotsDialog`, `ArchDiskCacheUpdater`, `ArchCompilationOptimizer`, `DebianViewBridge`, `DatabaseUpdater`, `.__init__`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `SoftwarePackage` connect `SoftwarePackage` to `PackageView`, `I18n`, `AsyncAction`, `FlatpakApplication`, `AsyncAction`, `SoftwareManager`, `CustomSoftwareAction`, `ArchPackage`, `manage_window.py`, `ManageWindow`, `ArchManager`, `ProcessWatcher`, `WindowActionsMixin`, `GenericSoftwareManager`, `TransactionContext`, `UpgradeRequirement`, `GitHubManager`, `debian/controller.py`, `DebianPackageManager`, `arch/controller.py`, `DebianPackage`, `AppImage`, `WebApplicationManager`, `WebApplication`, `threads/util.py`, `EopkgPackage`, `GitHubPackage`, `AppImageManager`, `DiskCacheLoader`, `SearchResult`, `SnapManager`, `FlatpakManager`, `manage.py`, `systray.py`, `AsyncDiskCacheLoader`, `NullLoggerFactory`, `.downgrade`, `.read_installed`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `SoftwareManager` connect `SoftwareManager` to `PackageView`, `I18n`, `AsyncAction`, `HttpClient`, `get_human_size_str`, `SoftwarePackage`, `AsyncAction`, `CustomSoftwareAction`, `manage_window.py`, `FormComponent`, `ManageWindow`, `ArchManager`, `ProcessWatcher`, `GenericSoftwareManager`, `SettingsWindow`, `GitHubManager`, `debian/controller.py`, `MemoryCache`, `DebianPackageManager`, `ApplicationContext`, `arch/controller.py`, `CategoriesDownloader`, `PreparePanel`, `WebApplicationManager`, `threads/util.py`, `TaskManager`, `AppImageManager`, `DiskCacheLoader`, `AsyncAction`, `SearchResult`, `SnapManager`, `PackageUpdate`, `FlatpakManager`, `manage.py`, `AnimateProgress`, `CoreConfigManager`, `.__init__`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 142 inferred relationships involving `I18n` (e.g. with `ApplicationContext` and `CreateConfigFile`) actually correct?**
  _`I18n` has 142 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `SoftwareManager` (e.g. with `ApplicationContext` and `DiskCacheLoader`) actually correct?**
  _`SoftwareManager` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 89 inferred relationships involving `PackageView` (e.g. with `PackagesTable` and `UpgradeToggleButton`) actually correct?**
  _`PackageView` has 89 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `SoftwarePackage` (e.g. with `SoftwareManager` and `TransactionResult`) actually correct?**
  _`SoftwarePackage` has 29 INFERRED edges - model-reasoned connections that need verification._