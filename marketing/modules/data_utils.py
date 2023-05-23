
csp = {"AE": "Agriculteurs exploitants",
       "ACCE": "Artisants, commercants, chefs d'entreprise",
       "CPIS": "Cadres et professions intellectuelles supérieures",
       "PI": "Professions intermédiaires",
       "E": "Employés",
       "O": "Ouvriers",
       "R": "Retraités",
       "SAP": "Sans activité professionnelle"}


def get_libelle_csp_from_initials(initials):
    return csp.get(initials, None)