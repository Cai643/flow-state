
print("Test Start")
try:
    from PySide6 import QtWidgets
    print("PySide6 imported")
except ImportError:
    print("PySide6 failed, trying PyQt5")
    try:
        from PyQt5 import QtWidgets
        print("PyQt5 imported")
    except ImportError:
        print("PyQt5 failed")

print("Test End")
