"""ICAO Aircraft Type Code Validator

This module provides validation for ICAO aircraft type designators based on
ICAO Document 8643 - Aircraft Type Designators.

The list includes common general aviation and commercial aircraft types
that are likely to appear in pilot logbooks.
"""

from typing import Set, Dict, Optional

# Common ICAO Aircraft Type Designators
# Based on ICAO Doc 8643 and common aircraft in pilot logbooks
VALID_ICAO_CODES: Dict[str, Dict[str, str]] = {
    # Cessna Aircraft
    "C150": {"manufacturer": "Cessna", "model": "150", "category": "Light Single-Engine"},
    "C152": {"manufacturer": "Cessna", "model": "152", "category": "Light Single-Engine"},
    "C162": {"manufacturer": "Cessna", "model": "162 Skycatcher", "category": "Light Single-Engine"},
    "C172": {"manufacturer": "Cessna", "model": "172 Skyhawk", "category": "Light Single-Engine"},
    "C175": {"manufacturer": "Cessna", "model": "175", "category": "Light Single-Engine"},
    "C177": {"manufacturer": "Cessna", "model": "177 Cardinal", "category": "Light Single-Engine"},
    "C180": {"manufacturer": "Cessna", "model": "180", "category": "Light Single-Engine"},
    "C182": {"manufacturer": "Cessna", "model": "182 Skylane", "category": "Light Single-Engine"},
    "C185": {"manufacturer": "Cessna", "model": "185", "category": "Light Single-Engine"},
    "C206": {"manufacturer": "Cessna", "model": "206", "category": "Light Single-Engine"},
    "C207": {"manufacturer": "Cessna", "model": "207", "category": "Light Single-Engine"},
    "C208": {"manufacturer": "Cessna", "model": "208 Caravan", "category": "Light Turboprop"},
    "C210": {"manufacturer": "Cessna", "model": "210 Centurion", "category": "Light Single-Engine"},
    "C310": {"manufacturer": "Cessna", "model": "310", "category": "Light Twin-Engine"},
    "C337": {"manufacturer": "Cessna", "model": "337 Skymaster", "category": "Light Twin-Engine"},
    "C340": {"manufacturer": "Cessna", "model": "340", "category": "Light Twin-Engine"},
    "C402": {"manufacturer": "Cessna", "model": "402", "category": "Light Twin-Engine"},
    "C414": {"manufacturer": "Cessna", "model": "414", "category": "Light Twin-Engine"},
    "C421": {"manufacturer": "Cessna", "model": "421", "category": "Light Twin-Engine"},
    "C441": {"manufacturer": "Cessna", "model": "441 Conquest", "category": "Light Turboprop"},
    "C500": {"manufacturer": "Cessna", "model": "Citation I", "category": "Light Jet"},
    "C525": {"manufacturer": "Cessna", "model": "CitationJet", "category": "Light Jet"},
    "C550": {"manufacturer": "Cessna", "model": "Citation II", "category": "Light Jet"},
    "C560": {"manufacturer": "Cessna", "model": "Citation V", "category": "Light Jet"},
    "C650": {"manufacturer": "Cessna", "model": "Citation III", "category": "Mid-Size Jet"},
    "C680": {"manufacturer": "Cessna", "model": "Citation Sovereign", "category": "Mid-Size Jet"},
    "C750": {"manufacturer": "Cessna", "model": "Citation X", "category": "Large Jet"},

    # Piper Aircraft
    "PA18": {"manufacturer": "Piper", "model": "J-3 Cub", "category": "Light Single-Engine"},
    "PA20": {"manufacturer": "Piper", "model": "Pacer", "category": "Light Single-Engine"},
    "PA22": {"manufacturer": "Piper", "model": "Tri-Pacer", "category": "Light Single-Engine"},
    "PA24": {"manufacturer": "Piper", "model": "Comanche", "category": "Light Single-Engine"},
    "PA25": {"manufacturer": "Piper", "model": "Pawnee", "category": "Agricultural"},
    "PA28": {"manufacturer": "Piper", "model": "Cherokee/Warrior/Archer", "category": "Light Single-Engine"},
    "PA30": {"manufacturer": "Piper", "model": "Twin Comanche", "category": "Light Twin-Engine"},
    "PA31": {"manufacturer": "Piper", "model": "Navajo", "category": "Light Twin-Engine"},
    "PA32": {"manufacturer": "Piper", "model": "Cherokee Six/Saratoga", "category": "Light Single-Engine"},
    "PA34": {"manufacturer": "Piper", "model": "Seneca", "category": "Light Twin-Engine"},
    "PA36": {"manufacturer": "Piper", "model": "Pawnee Brave", "category": "Agricultural"},
    "PA38": {"manufacturer": "Piper", "model": "Tomahawk", "category": "Light Single-Engine"},
    "PA44": {"manufacturer": "Piper", "model": "Seminole", "category": "Light Twin-Engine"},
    "PA46": {"manufacturer": "Piper", "model": "Malibu/Mirage/Matrix", "category": "Light Single-Engine"},

    # Beechcraft
    "B190": {"manufacturer": "Beechcraft", "model": "King Air 100", "category": "Light Turboprop"},
    "B200": {"manufacturer": "Beechcraft", "model": "King Air 200", "category": "Light Turboprop"},
    "B300": {"manufacturer": "Beechcraft", "model": "King Air 350", "category": "Light Turboprop"},
    "BE20": {"manufacturer": "Beechcraft", "model": "King Air", "category": "Light Turboprop"},
    "BE23": {"manufacturer": "Beechcraft", "model": "Musketeer/Sundowner", "category": "Light Single-Engine"},
    "BE24": {"manufacturer": "Beechcraft", "model": "Sierra", "category": "Light Single-Engine"},
    "BE33": {"manufacturer": "Beechcraft", "model": "Debonair/Bonanza", "category": "Light Single-Engine"},
    "BE35": {"manufacturer": "Beechcraft", "model": "Bonanza", "category": "Light Single-Engine"},
    "BE36": {"manufacturer": "Beechcraft", "model": "Bonanza A36", "category": "Light Single-Engine"},
    "BE40": {"manufacturer": "Beechcraft", "model": "Beechjet 400", "category": "Light Jet"},
    "BE55": {"manufacturer": "Beechcraft", "model": "Baron", "category": "Light Twin-Engine"},
    "BE58": {"manufacturer": "Beechcraft", "model": "Baron", "category": "Light Twin-Engine"},
    "BE76": {"manufacturer": "Beechcraft", "model": "Duchess", "category": "Light Twin-Engine"},
    "BE77": {"manufacturer": "Beechcraft", "model": "Skipper", "category": "Light Single-Engine"},
    "BE9L": {"manufacturer": "Beechcraft", "model": "King Air 90", "category": "Light Turboprop"},
    "BE9T": {"manufacturer": "Beechcraft", "model": "King Air 90", "category": "Light Turboprop"},

    # Cirrus Aircraft
    "SR20": {"manufacturer": "Cirrus", "model": "SR20", "category": "Light Single-Engine"},
    "SR22": {"manufacturer": "Cirrus", "model": "SR22", "category": "Light Single-Engine"},
    "SF50": {"manufacturer": "Cirrus", "model": "Vision Jet", "category": "Light Jet"},

    # Diamond Aircraft
    "DA20": {"manufacturer": "Diamond", "model": "Katana", "category": "Light Single-Engine"},
    "DA40": {"manufacturer": "Diamond", "model": "Diamond Star", "category": "Light Single-Engine"},
    "DA42": {"manufacturer": "Diamond", "model": "Twin Star", "category": "Light Twin-Engine"},
    "DA62": {"manufacturer": "Diamond", "model": "DA62", "category": "Light Twin-Engine"},

    # American Champion (Citabria, Decathlon)
    "CH7A": {"manufacturer": "American Champion", "model": "7ECA Citabria", "category": "Aerobatic"},
    "CH7B": {"manufacturer": "American Champion", "model": "7GCAA Citabria", "category": "Aerobatic"},
    "CH7C": {"manufacturer": "American Champion", "model": "7GCBC Citabria", "category": "Aerobatic"},
    "CH7E": {"manufacturer": "American Champion", "model": "7ECA Citabria", "category": "Aerobatic"},
    "CH7G": {"manufacturer": "American Champion", "model": "7GCAA Citabria", "category": "Aerobatic"},
    "CH7K": {"manufacturer": "American Champion", "model": "7KCAB Citabria", "category": "Aerobatic"},
    "CH8A": {"manufacturer": "American Champion", "model": "8KCAB Decathlon", "category": "Aerobatic"},
    "CH8G": {"manufacturer": "American Champion", "model": "8GCBC Scout", "category": "Light Single-Engine"},
    "BL8": {"manufacturer": "American Champion", "model": "8KCAB Decathlon", "category": "Aerobatic"},

    # Mooney
    "M20C": {"manufacturer": "Mooney", "model": "M20C Ranger", "category": "Light Single-Engine"},
    "M20E": {"manufacturer": "Mooney", "model": "M20E Super 21", "category": "Light Single-Engine"},
    "M20F": {"manufacturer": "Mooney", "model": "M20F Executive 21", "category": "Light Single-Engine"},
    "M20J": {"manufacturer": "Mooney", "model": "M20J 201", "category": "Light Single-Engine"},
    "M20K": {"manufacturer": "Mooney", "model": "M20K 231", "category": "Light Single-Engine"},
    "M20M": {"manufacturer": "Mooney", "model": "M20M TLS", "category": "Light Single-Engine"},
    "M20R": {"manufacturer": "Mooney", "model": "M20R Ovation", "category": "Light Single-Engine"},
    "M20S": {"manufacturer": "Mooney", "model": "M20S Eagle", "category": "Light Single-Engine"},
    "M20T": {"manufacturer": "Mooney", "model": "M20T Acclaim", "category": "Light Single-Engine"},

    # Grumman/American General
    "AA1": {"manufacturer": "Grumman", "model": "AA-1 Yankee", "category": "Light Single-Engine"},
    "AA1A": {"manufacturer": "Grumman", "model": "AA-1A Trainer", "category": "Light Single-Engine"},
    "AA1B": {"manufacturer": "Grumman", "model": "AA-1B Trainer", "category": "Light Single-Engine"},
    "AA1C": {"manufacturer": "Grumman", "model": "AA-1C Lynx", "category": "Light Single-Engine"},
    "AA5A": {"manufacturer": "Grumman", "model": "AA-5A Cheetah", "category": "Light Single-Engine"},
    "AA5B": {"manufacturer": "Grumman", "model": "AA-5B Tiger", "category": "Light Single-Engine"},
    "AG5B": {"manufacturer": "American General", "model": "AG-5B Tiger", "category": "Light Single-Engine"},

    # Vans Aircraft (Experimental)
    "RV3": {"manufacturer": "Van's", "model": "RV-3", "category": "Experimental"},
    "RV4": {"manufacturer": "Van's", "model": "RV-4", "category": "Experimental"},
    "RV6": {"manufacturer": "Van's", "model": "RV-6", "category": "Experimental"},
    "RV7": {"manufacturer": "Van's", "model": "RV-7", "category": "Experimental"},
    "RV8": {"manufacturer": "Van's", "model": "RV-8", "category": "Experimental"},
    "RV9": {"manufacturer": "Van's", "model": "RV-9", "category": "Experimental"},
    "RV10": {"manufacturer": "Van's", "model": "RV-10", "category": "Experimental"},
    "RV12": {"manufacturer": "Van's", "model": "RV-12", "category": "Light Sport"},
    "RV14": {"manufacturer": "Van's", "model": "RV-14", "category": "Experimental"},

    # Maule Aircraft
    "M4": {"manufacturer": "Maule", "model": "M-4", "category": "Light Single-Engine"},
    "M5": {"manufacturer": "Maule", "model": "M-5", "category": "Light Single-Engine"},
    "M6": {"manufacturer": "Maule", "model": "M-6", "category": "Light Single-Engine"},
    "M7": {"manufacturer": "Maule", "model": "M-7", "category": "Light Single-Engine"},
    "M8": {"manufacturer": "Maule", "model": "M-8", "category": "Light Single-Engine"},
    "M9": {"manufacturer": "Maule", "model": "M-9", "category": "Light Single-Engine"},

    # Socata/Daher
    "TBM7": {"manufacturer": "Socata", "model": "TBM 700", "category": "Light Turboprop"},
    "TBM8": {"manufacturer": "Socata", "model": "TBM 800", "category": "Light Turboprop"},
    "TBM9": {"manufacturer": "Daher", "model": "TBM 900", "category": "Light Turboprop"},
    "TB10": {"manufacturer": "Socata", "model": "TB 10 Tobago", "category": "Light Single-Engine"},
    "TB20": {"manufacturer": "Socata", "model": "TB 20 Trinidad", "category": "Light Single-Engine"},
    "TB21": {"manufacturer": "Socata", "model": "TB 21 Trinidad TC", "category": "Light Single-Engine"},

    # Extra Aircraft (Aerobatic)
    "EA30": {"manufacturer": "Extra", "model": "EA-300", "category": "Aerobatic"},
    "EA32": {"manufacturer": "Extra", "model": "EA-330", "category": "Aerobatic"},

    # Pitts Special (Aerobatic)
    "PTS1": {"manufacturer": "Pitts", "model": "S-1 Special", "category": "Aerobatic"},
    "PTS2": {"manufacturer": "Pitts", "model": "S-2 Special", "category": "Aerobatic"},

    # Gliders (Common Training Gliders)
    "ASK13": {"manufacturer": "Alexander Schleicher", "model": "ASK 13", "category": "Glider"},
    "ASK21": {"manufacturer": "Alexander Schleicher", "model": "ASK 21", "category": "Glider"},
    "K21": {"manufacturer": "Alexander Schleicher", "model": "ASK 21", "category": "Glider"},
    "SGS233": {"manufacturer": "Schweizer", "model": "SGS 2-33", "category": "Glider"},
    "SGS126": {"manufacturer": "Schweizer", "model": "SGS 1-26", "category": "Glider"},

    # Light Sport Aircraft
    "CTLS": {"manufacturer": "Flight Design", "model": "CT-LS", "category": "Light Sport"},
    "FK9": {"manufacturer": "FK Lightplanes", "model": "FK9", "category": "Light Sport"},
    "RANS": {"manufacturer": "RANS", "model": "S-6ES Coyote II", "category": "Light Sport"},

    # Vintage/Warbird Aircraft
    "BT-13": {"manufacturer": "Vultee", "model": "BT-13 Valiant", "category": "Vintage Trainer"},
    "BT13": {"manufacturer": "Vultee", "model": "BT-13 Valiant", "category": "Vintage Trainer"},

    # Helicopters (Common Training)
    "R22": {"manufacturer": "Robinson", "model": "R22", "category": "Helicopter"},
    "R44": {"manufacturer": "Robinson", "model": "R44", "category": "Helicopter"},
    "R66": {"manufacturer": "Robinson", "model": "R66", "category": "Helicopter"},
    "H269": {"manufacturer": "Hughes/Schweizer", "model": "269/300", "category": "Helicopter"},
    "S300": {"manufacturer": "Schweizer", "model": "S-300", "category": "Helicopter"},

    # Commercial Aircraft (for ATP/Airline pilots)
    "B737": {"manufacturer": "Boeing", "model": "737", "category": "Commercial Jet"},
    "B738": {"manufacturer": "Boeing", "model": "737-800", "category": "Commercial Jet"},
    "B739": {"manufacturer": "Boeing", "model": "737-900", "category": "Commercial Jet"},
    "B752": {"manufacturer": "Boeing", "model": "757-200", "category": "Commercial Jet"},
    "B763": {"manufacturer": "Boeing", "model": "767-300", "category": "Commercial Jet"},
    "B772": {"manufacturer": "Boeing", "model": "777-200", "category": "Commercial Jet"},
    "B773": {"manufacturer": "Boeing", "model": "777-300", "category": "Commercial Jet"},
    "B787": {"manufacturer": "Boeing", "model": "787 Dreamliner", "category": "Commercial Jet"},
    "A319": {"manufacturer": "Airbus", "model": "A319", "category": "Commercial Jet"},
    "A320": {"manufacturer": "Airbus", "model": "A320", "category": "Commercial Jet"},
    "A321": {"manufacturer": "Airbus", "model": "A321", "category": "Commercial Jet"},
    "A330": {"manufacturer": "Airbus", "model": "A330", "category": "Commercial Jet"},
    "A350": {"manufacturer": "Airbus", "model": "A350", "category": "Commercial Jet"},
    "E145": {"manufacturer": "Embraer", "model": "ERJ 145", "category": "Regional Jet"},
    "E170": {"manufacturer": "Embraer", "model": "E-Jet 170", "category": "Regional Jet"},
    "E175": {"manufacturer": "Embraer", "model": "E-Jet 175", "category": "Regional Jet"},
    "CRJ2": {"manufacturer": "Bombardier", "model": "CRJ-200", "category": "Regional Jet"},
    "CRJ7": {"manufacturer": "Bombardier", "model": "CRJ-700", "category": "Regional Jet"},
    "CRJ9": {"manufacturer": "Bombardier", "model": "CRJ-900", "category": "Regional Jet"},
    "DH8A": {"manufacturer": "De Havilland", "model": "Dash 8-100", "category": "Regional Turboprop"},
    "DH8B": {"manufacturer": "De Havilland", "model": "Dash 8-200", "category": "Regional Turboprop"},
    "DH8C": {"manufacturer": "De Havilland", "model": "Dash 8-300", "category": "Regional Turboprop"},
    "DH8D": {"manufacturer": "De Havilland", "model": "Dash 8-400", "category": "Regional Turboprop"},
    "AT72": {"manufacturer": "ATR", "model": "ATR 72", "category": "Regional Turboprop"},
    "AT42": {"manufacturer": "ATR", "model": "ATR 42", "category": "Regional Turboprop"},
}


def is_valid_icao_code(code: str) -> bool:
    """
    Check if an ICAO aircraft type code is valid.
    
    Args:
        code: The ICAO aircraft type code to validate
        
    Returns:
        True if the code is valid, False otherwise
    """
    if not code:
        return False
    
    # Convert to uppercase for comparison
    code_upper = code.upper().strip()
    
    return code_upper in VALID_ICAO_CODES


def get_icao_info(code: str) -> Optional[Dict[str, str]]:
    """
    Get information about an ICAO aircraft type code.
    
    Args:
        code: The ICAO aircraft type code
        
    Returns:
        Dictionary with manufacturer, model, and category info, or None if invalid
    """
    if not code:
        return None
    
    code_upper = code.upper().strip()
    return VALID_ICAO_CODES.get(code_upper)


def suggest_similar_codes(code: str, max_suggestions: int = 5) -> list[str]:
    """
    Suggest similar ICAO codes for a potentially misspelled code.
    
    Args:
        code: The potentially incorrect ICAO code
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of similar valid ICAO codes
    """
    if not code:
        return []
    
    code_upper = code.upper().strip()
    suggestions = []
    
    # Look for codes that start with the same characters
    for valid_code in VALID_ICAO_CODES.keys():
        if len(suggestions) >= max_suggestions:
            break
            
        # Check if codes start with same characters
        if len(code_upper) >= 2 and valid_code.startswith(code_upper[:2]):
            suggestions.append(valid_code)
        # Check if codes are similar length and have common characters
        elif (abs(len(valid_code) - len(code_upper)) <= 1 and 
              len(set(code_upper) & set(valid_code)) >= len(code_upper) // 2):
            suggestions.append(valid_code)
    
    return suggestions[:max_suggestions]


def get_all_codes_by_manufacturer(manufacturer: str) -> list[str]:
    """
    Get all ICAO codes for a specific manufacturer.
    
    Args:
        manufacturer: The aircraft manufacturer name
        
    Returns:
        List of ICAO codes for that manufacturer
    """
    manufacturer_lower = manufacturer.lower()
    codes = []
    
    for code, info in VALID_ICAO_CODES.items():
        if info["manufacturer"].lower() == manufacturer_lower:
            codes.append(code)
    
    return sorted(codes)


def get_validation_summary() -> Dict[str, int]:
    """
    Get a summary of the ICAO validation database.
    
    Returns:
        Dictionary with counts by category
    """
    categories = {}
    manufacturers = set()
    
    for info in VALID_ICAO_CODES.values():
        category = info["category"]
        manufacturer = info["manufacturer"]
        
        categories[category] = categories.get(category, 0) + 1
        manufacturers.add(manufacturer)
    
    return {
        "total_codes": len(VALID_ICAO_CODES),
        "categories": categories,
        "manufacturers_count": len(manufacturers)
    }


def get_validation_error_message(code: str) -> str:
    """
    Generate a helpful error message for invalid ICAO codes.
    
    Args:
        code: The invalid ICAO code
        
    Returns:
        Formatted error message with suggestions and resources
    """
    if not code:
        return "Missing ICAO aircraft type code"
    
    code_upper = code.upper().strip()
    suggestions = suggest_similar_codes(code_upper)
    
    message = f"Invalid ICAO aircraft type code: '{code_upper}'"
    
    if suggestions:
        message += f". Similar codes: {', '.join(suggestions)}"
    
    message += (
        f". Verify at: https://www.icaodesignators.com/ or "
        f"https://skybrary.aero/aircraft-types"
    )
    
    return message


# Official ICAO resources for reference
ICAO_RESOURCES = {
    "official_database": "https://www.icao.int/safety/OPS/OPS-Section/Pages/aircraft-type-designators.aspx",
    "searchable_database": "https://www.icaodesignators.com/",
    "skybrary_reference": "https://skybrary.aero/aircraft-types",
    "faa_reference": "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/",
    "contact_email": "ICAOAPI@icao.int"
}
