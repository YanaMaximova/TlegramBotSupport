#  <#Title#>
from firebase.firebase import read_document_with_filter
def farmer2agronom(farmer_tg_id):
    agronomists = read_document_with_filter("available_farmers", "array_contains", farmer_tg_id)
    if len(agronomists):
        return agronomists[0]["data"]["tg_id"]
    else:
        return None
