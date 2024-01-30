import win32print

# Enumerate and list available printers
printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)

for printer_info in printers:
    printer_name = printer_info[2]
    printer_description = printer_info[1]
    printer_location = printer_info[3]

    print("Printer Name:", printer_name)
    print("Printer Description:", printer_description)
    print("Printer Location:", printer_location)
    print("")

# You can access other printer properties from the tuple as needed.
