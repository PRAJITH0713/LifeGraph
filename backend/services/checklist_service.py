"""Prepare safe checklist responses from catalogue service records."""


def build_checklist(service):
	requirements = service["requirements"]
	return {
		"service_id": service["id"],
		"requirements": requirements,
		"category": service["category"],
		"responsible_authority": service["responsible_authority"],
		"official_portal_url": service["official_portal_url"],
		"verification_status": service["requirement_verification_status"],
		"requirement_verification_status": service["requirement_verification_status"],
		"message": (
			"Needs verification: no official proof requirements are confirmed."
			if service["requirement_verification_status"] != "verified" or not requirements
			else None
		),
	}