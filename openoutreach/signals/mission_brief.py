def recommended_next_steps(organization, funding_criteria=None) -> list[str]:
    """Return deterministic executive next steps from current analyzer results."""
    steps = ["Review and confirm the inferred organization profile."]
    if not organization.city and not organization.county and not organization.state:
        steps.append("Confirm service geography to improve local funding matches.")
    if not organization.outcomes_and_impact:
        steps.append("Prepare outcome and impact data to strengthen funding readiness.")
    if funding_criteria and funding_criteria.focus_areas:
        steps.append("Use the generated funding themes for opportunity discovery.")
    else:
        steps.append("Run or refine organization analysis before opportunity discovery.")
    return steps
