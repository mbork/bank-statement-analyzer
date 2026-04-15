# * UI constants

from PySide6.QtCore import QDate

# ** Date sentinel values
# Used as "no date set" sentinels in date filter widgets.
# Values are intentionally out of range for real bank data.

MIN_DATE = QDate(1901, 1, 1)
MAX_DATE = QDate(2099, 12, 31)
