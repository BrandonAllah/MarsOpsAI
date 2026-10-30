"""NASA-sourced facts and journal state for a condensed Mars simulation."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Discovery:
    id: str
    name: str
    description: str
    significance: str
    source_url: str
    position: tuple
    location: str = "Mars"
    image_file: str = ""
    image_url: str = ""
    image_source_url: str = ""
    image_credit: str = ""
    image_caption: str = ""
    image_mission: str = ""


DISCOVERIES = (
    Discovery(
        "jezero", "Jezero Crater",
        "Perseverance explored Jezero Crater, where sediments were deposited in a delta as a river entered an ancient lake.",
        "The deposits help scientists reconstruct Mars' history of water.",
        "https://science.nasa.gov/mission/mars-2020-perseverance/science-highlights/",
        (700, 660), "Jezero Crater",
        "jezero.jpg", "https://assets.science.nasa.gov/assets/science/psd/photojournal/pia/pia24/pia24683/PIA24683.jpg",
        "https://science.nasa.gov/photojournal/mars-delta-scarp-from-more-than-a-mile-away/",
        "NASA/JPL-Caltech/LANL/CNES/CNRS/ASU/MSSS",
        "Perseverance's five-image mosaic of Jezero Crater's Delta Scarp, captured in 2021.", "Mars 2020 / Perseverance",
    ),
    Discovery(
        "cheyava", "Cheyava Falls",
        "Perseverance studied this rock and its light-colored, dark-rimmed leopard spots. Its Sapphire Canyon sample contains potential biosignatures.",
        "These clues could have a biological origin, but other explanations remain possible. They do not confirm life; further study is needed.",
        "https://science.nasa.gov/mars/the-mars-report/2025-september-special-edition/",
        (1500, 455), "Jezero Crater",
        "cheyava.jpg", "https://assets.science.nasa.gov/assets/science/psd/photojournal/pia/pia26/pia26368/jpeg/PIA26368.jpg",
        "https://science.nasa.gov/photojournal/perseverance-finds-a-rock-with-leopard-spots/",
        "NASA/JPL-Caltech/MSSS",
        "Perseverance's WATSON camera imaged the Cheyava Falls rock and its leopard spots in 2024.", "Mars 2020 / Perseverance",
    ),
    Discovery(
        "blueberries", "Martian Blueberries",
        "Opportunity examined small spherical concretions nicknamed blueberries and identified the iron-bearing mineral hematite.",
        "Their hematite-rich grains provide evidence of past water-related processes at Meridiani Planum.",
        "https://science.nasa.gov/resource/discovery-served-up-in-a-bowl/",
        (1500, 1225), "Meridiani Planum",
        "blueberries.jpg", "https://assets.science.nasa.gov/assets/science/psd/photojournal/pia/pia05/pia05634/PIA05634.jpg",
        "https://science.nasa.gov/photojournal/discovery-served-up-in-a-bowl/",
        "NASA/JPL/Cornell",
        "Opportunity's approximate true-color view of the blueberry-rich Berry Bowl rock in Eagle Crater.", "Mars Exploration Rovers / Opportunity",
    ),
    Discovery(
        "sheepbed", "Sheepbed Mudstone",
        "Curiosity studied the Sheepbed mudstone in Yellowknife Bay, Gale Crater, including a rock called John Klein.",
        "Scientists interpret the mudstone as an ancient lake deposit; its chemistry indicates a potentially habitable environment, not confirmed life.",
        "https://science.nasa.gov/resource/view-into-john-klein-drill-hole-in-martian-mudstone/",
        (1000, 800), "Yellowknife Bay, Gale Crater",
        "sheepbed.jpg", "https://assets.science.nasa.gov/assets/science/psd/photojournal/pia/pia17/pia17594/PIA17594.jpg",
        "https://science.nasa.gov/photojournal/view-into-john-klein-drill-hole-in-martian-mudstone/",
        "NASA/JPL-Caltech/MSSS",
        "Curiosity's close-up of the John Klein drill hole in the Sheepbed mudstone, photographed in 2013.", "Mars Science Laboratory / Curiosity",
    ),
    Discovery(
        "mountsharp", "Mount Sharp Sulfates",
        "Curiosity explored a sulfate-bearing layer on Mount Sharp in Gale Crater.",
        "The mineral-rich layers help scientists study how the Martian environment changed over time.",
        "https://science.nasa.gov/resource/mount-sharp-comes-in-sharply/",
        (1200, 1000), "Mount Sharp, Gale Crater",
        "mountsharp.jpg", "https://assets.science.nasa.gov/assets/science/psd/photojournal/pia/pia25/pia25367/PIA25367.jpg",
        "https://science.nasa.gov/photojournal/curiositys-view-of-sulfate-bearing-region-and-streambed-rocks/",
        "NASA/JPL-Caltech/MSSS",
        "Curiosity's 2022 mosaic shows a sulfate-bearing region ahead on Mount Sharp and dark streambed rocks.", "Mars Science Laboratory / Curiosity",
    ),
)

INTERACTION_RADIUS = 90


def nearest_discovery(position, discoveries=DISCOVERIES, radius=INTERACTION_RADIUS):
    """Return the closest landmark in reach, with stable ordering for ties."""
    nearby = [item for item in discoveries if math.dist(position, item.position) <= radius]
    return min(nearby, key=lambda item: math.dist(position, item.position), default=None)


def interaction_choice(rover, samples, scanner_range, discoveries=DISCOVERIES):
    """Samples take priority; a later E press can investigate the landmark."""
    reach = rover.inflate(scanner_range * 2, scanner_range * 2)
    if any(reach.colliderect(sample) for sample in samples):
        return "sample", None
    discovery = nearest_discovery(rover.center, discoveries)
    return ("discovery", discovery) if discovery else (None, None)


class DiscoveryJournal:
    def __init__(self, discoveries=DISCOVERIES):
        self.discoveries = discoveries
        self.found = set()
        self.selected = 0
        self.is_open = False

    def investigate(self, discovery):
        self.found.add(discovery.id)
        self.selected = next(i for i, item in enumerate(self.discoveries) if item.id == discovery.id)

    def toggle(self):
        self.is_open = not self.is_open

    def move(self, amount):
        self.selected = (self.selected + amount) % len(self.discoveries)

    @property
    def current(self):
        return self.discoveries[self.selected]

    def is_found(self, discovery):
        return discovery.id in self.found
