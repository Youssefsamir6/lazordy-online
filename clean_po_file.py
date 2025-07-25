import polib

# Load your original broken .po file
po = polib.pofile('locale/ar/LC_MESSAGES/django.po')

# Define a list of invalid msgid patterns (you can expand this list)
invalid_entries = [
    "", ".", ":", "name", "value", "s", "Referer", "select", "object", "true",
    "false", "null", "None", "type", "csrf", "data", "class", "id", "input", "GET", "POST"
]

# Filter out bad entries
cleaned_entries = [entry for entry in po if entry.msgid not in invalid_entries and len(entry.msgid.strip()) > 1]

# Create a new PO file to save the cleaned content
cleaned_po = polib.POFile()
cleaned_po.metadata = po.metadata

for entry in cleaned_entries:
    cleaned_po.append(entry)

# Save to a new file
cleaned_po.save('locale/ar/LC_MESSAGES/django_cleaned.po')
print("Cleaned PO file saved as django_cleaned.po")
