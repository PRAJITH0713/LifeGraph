"""Prepare safe checklist responses from catalogue service records."""


def build_checklist(service):
	requirements = service["requirements"]
	return {
		"service_id": service["id"],
		"requirements": requirements,
		"verification_status": service["verification_status"],
		"message": (
			"Needs verification: no official proof requirements are confirmed."
			if service["verification_status"] != "verified" or not requirements
			else None
		),
	}