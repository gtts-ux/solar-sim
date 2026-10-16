"""Offline astronomy catalogue. Rounded educational values; see SOURCES.txt."""
from dataclasses import dataclass
import math

G = 6.67430e-11
AU_KM = 149597870.7
CATALOG_DATE = "2026-10-16"


@dataclass(frozen=True)
class Body:
    name: str
    kind: str
    parent: str | None
    mass: float                 # kg
    radius: float               # mean radius, km
    orbit: float                # semi-major axis about parent, km
    period: float               # sidereal orbital period, Earth days
    rotation: float             # sidereal rotation, hours; negative = retrograde
    temperature: str
    composition: str
    atmosphere: str
    features: str
    color: int = 6              # curses basic color
    known_moons: int = 0
    rings: str = "None"
    eccentricity: float = 0.0
    tilt: float | None = None
    estimated_mass: bool = False

    @property
    def gravity(self):
        return G * self.mass / (self.radius * 1000) ** 2

    @property
    def density(self):
        return self.mass / (4 / 3 * math.pi * (self.radius * 1000) ** 3)

    @property
    def escape(self):
        return math.sqrt(2 * G * self.mass / (self.radius * 1000)) / 1000


SUN = Body("Sun", "G2 V star", None, 1.9885e30, 695700, 0, 0, 609.12,
           "~5,500 C photosphere; ~15 million C core",
           "Hydrogen and helium plasma; smaller amounts of heavier elements.",
           "Photosphere, chromosphere and extremely hot corona; solar wind flows outward.",
           "Core fusion powers the system. Rotation varies with latitude: about 25 days at the equator.", 3)

PLANETS = [
    Body("Mercury", "Terrestrial planet", "Sun", 3.3011e23, 2439.7, .38709927 * AU_KM, 87.969,
         1407.6, "~167 C mean; roughly -180 to 430 C surface extremes",
         "Large iron-rich core beneath a thin rocky mantle and silicate crust.",
         "Very thin exosphere containing oxygen, sodium, hydrogen, helium and potassium.",
         "Cratered terrain and enormous fault scarps. Three rotations for every two orbits.", 7,
         eccentricity=.2056, tilt=.034),
    Body("Venus", "Terrestrial planet", "Sun", 4.8675e24, 6051.8, .72333566 * AU_KM, 224.701,
         -5832.5, "~464 C surface mean",
         "Iron core, rocky mantle and volcanic silicate crust.",
         "~96.5% carbon dioxide, ~3.5% nitrogen; sulfuric-acid clouds; ~92 bar at surface.",
         "A strong greenhouse effect creates the hottest planetary surface. Very slow retrograde spin.", 3,
         eccentricity=.0068, tilt=177.4),
    Body("Earth", "Terrestrial planet", "Sun", 5.9722e24, 6371.0, 1.00000261 * AU_KM, 365.256,
         23.9345, "~15 C global surface mean",
         "Iron-nickel core, silicate mantle and crust; liquid water covers most of the surface.",
         "~78% nitrogen, ~21% oxygen, with argon, carbon dioxide and variable water vapor; ~1 bar.",
         "The only world currently known to host life. Plate tectonics and a protective magnetic field.", 4,
         known_moons=1, eccentricity=.0167, tilt=23.44),
    Body("Mars", "Terrestrial planet", "Sun", 6.4171e23, 3389.5, 1.52371034 * AU_KM, 686.980,
         24.6229, "~-65 C surface mean",
         "Iron-rich core, silicate mantle and basaltic crust; iron oxides color the dust.",
         "Thin, mostly carbon dioxide with nitrogen and argon; ~0.006 bar, varying with season.",
         "Olympus Mons, Valles Marineris, polar ice and evidence of ancient rivers and lakes.", 1,
         known_moons=2, eccentricity=.0934, tilt=25.19),
    Body("Jupiter", "Gas giant", "Sun", 1.8982e27, 69911, 5.202887 * AU_KM, 4332.59,
         9.925, "~-110 C representative cloud level",
         "Mostly hydrogen and helium; deep metallic hydrogen and a diffuse region rich in heavy elements.",
         "Hydrogen and helium with ammonia, water and methane traces; no solid surface.",
         "Largest planet; Great Red Spot, powerful magnetic field and the four Galilean moons.", 3,
         known_moons=115, rings="Faint dusty rings", eccentricity=.0484, tilt=3.13),
    Body("Saturn", "Gas giant", "Sun", 5.6834e26, 58232, 9.53667594 * AU_KM, 10759.22,
         10.7, "~-140 C representative cloud level",
         "Mostly hydrogen and helium, with a dense interior enriched in rock and ice-forming materials.",
         "Hydrogen and helium, with methane and ammonia traces; no solid surface.",
         "Low mean density. Its extensive rings are mainly water-ice particles, with some rock and dust.", 3,
         known_moons=293, rings="Bright main rings plus diffuse outer rings", eccentricity=.0539, tilt=26.73),
    Body("Uranus", "Ice giant", "Sun", 8.6810e25, 25362, 19.18916464 * AU_KM, 30688.5,
         -17.24, "~-195 C representative upper atmosphere",
         "Hydrogen-helium envelope above a deep interior rich in water, ammonia and methane materials.",
         "Hydrogen, helium and methane; methane absorbs red light. No solid accessible surface.",
         "Its extreme axial tilt produces unusual seasons; its magnetic field is tilted and offset.", 6,
         known_moons=29, rings="Narrow dark rings", eccentricity=.0473, tilt=97.77),
    Body("Neptune", "Ice giant", "Sun", 1.02413e26, 24622, 30.06992276 * AU_KM, 60182,
         16.11, "~-200 C representative upper atmosphere",
         "Rock-rich central region and a deep volatile-rich interior beneath hydrogen and helium.",
         "Hydrogen, helium and methane; high-altitude clouds and powerful winds. No solid surface.",
         "The most distant major planet. Triton travels in a retrograde orbit around it.", 4,
         known_moons=16, rings="Faint dusty rings and arcs", eccentricity=.0086, tilt=28.32),
]


DWARF_PLANETS = [
    Body("Ceres", "Dwarf planet", "Sun", 9.3835e20, 469.7, 2.7675*AU_KM, 1682.0,
         9.074, "~ -105 C representative surface",
         "Rock, water ice, hydrated minerals and salts; a differentiated interior.",
         "No substantial atmosphere; transient water vapor has been detected.",
         "Largest asteroid-belt object. Dawn mapped bright salt deposits and the mountain Ahuna Mons.",
         7, eccentricity=.0758, tilt=4.0),
    Body("Pluto", "Dwarf planet", "Sun", 1.303e22, 1188.3, 39.482*AU_KM, 90560,
         -153.293, "~ -230 C representative surface",
         "Rocky interior and water-ice crust, with nitrogen, methane and carbon-monoxide surface ices.",
         "Thin, variable nitrogen atmosphere with methane and carbon monoxide.",
         "New Horizons explored Pluto in 2015. Charon is its largest moon; the system is strongly binary.",
         3, known_moons=5, eccentricity=.2488, tilt=119.6),
    Body("Haumea", "Dwarf planet", "Sun", 4.006e21, 798, 43.116*AU_KM, 103774,
         3.9155, "~ -241 C representative surface",
         "Rock-rich interior with a water-ice surface. Radius is an approximate volume-equivalent value.",
         "No substantial atmosphere detected.",
         "Rapid spin creates a strongly elongated shape. Its moons are Hi'iaka and Namaka.",
         6, known_moons=2, rings="A narrow ring", eccentricity=.19),
    Body("Makemake", "Dwarf planet", "Sun", 3.1e21, 715, 45.79*AU_KM, 112897,
         22.8266, "~ -239 C representative surface",
         "Rock and ice; methane and ethane ices are detected on the surface. Mass is poorly constrained.",
         "No substantial global atmosphere detected.",
         "A bright Kuiper Belt world with the provisional moon S/2015 (136472) 1, nicknamed MK 2.",
         1, known_moons=1, eccentricity=.161, estimated_mass=True),
    Body("Eris", "Dwarf planet", "Sun", 1.6466e22, 1163, 67.864*AU_KM, 204199,
         15.7859*24, "Roughly -243 to -217 C",
         "Rock and ice with methane-rich surface frost; interior is poorly constrained.",
         "No substantial atmosphere detected at its current cold distance.",
         "A massive distant dwarf planet with the moon Dysnomia. Rotation is approximately synchronous with Dysnomia.",
         5, known_moons=1, eccentricity=.436),
]


def moon(name, parent, mass, radius, orbit, period, composition, atmosphere, features,
         temperature, eccentricity=0, retrograde=False, locked=True, estimated=False):
    return Body(name, "Natural satellite", parent, mass, radius, orbit, period,
                (-1 if retrograde else 1) * period * 24 if locked else 0,
                temperature, composition, atmosphere, features, 7,
                eccentricity=eccentricity, estimated_mass=estimated)


MOONS = [
    moon("Moon", "Earth", 7.342e22, 1737.4, 384400, 27.3217,
         "Silicate crust and mantle, small iron-rich core; basaltic maria and dusty regolith.",
         "Extremely thin exosphere; no breathable atmosphere.",
         "Tidally locked. Likely formed from debris following an early giant impact with Earth.",
         "Roughly -173 to 127 C at the equatorial surface", .0549),
    moon("Phobos", "Mars", 1.0659e16, 11.08, 9376, .31891,
         "Dark, porous rocky material; detailed interior composition remains uncertain.", "No substantial atmosphere.",
         "Irregular, heavily cratered and spiraling slowly toward Mars; prominent Stickney crater.",
         "Strong day/night variation; roughly -112 to -4 C", .0151),
    moon("Deimos", "Mars", 1.4762e15, 6.2, 23463, 1.26244,
         "Dark rocky material with a loose regolith cover; interior is poorly constrained.", "No substantial atmosphere.",
         "Smaller and more distant than Phobos, with a smoother-looking surface.", "Cold, airless surface", .0003),
    moon("Amalthea", "Jupiter", 2.08e18, 83.5, 181366, .49818,
         "Low-density, porous material; likely ice-bearing with dark surface material.", "No substantial atmosphere.",
         "An irregular reddish inner moon; contributes dust to Jupiter's faint rings.", "~ -153 C", .0032),
    moon("Io", "Jupiter", 8.9319e22, 1821.6, 421800, 1.76914,
         "Rocky mantle and iron-rich core; sulfur compounds and silicate lava at the surface.",
         "Thin, variable sulfur dioxide atmosphere.",
         "Intense tidal heating drives widespread volcanism. In a resonance with Europa and Ganymede.", "~ -143 C away from volcanic hot spots", .0041),
    moon("Europa", "Jupiter", 4.7998e22, 1560.8, 671100, 3.55118,
         "Water-ice shell, likely salty liquid ocean, silicate interior and metallic core.",
         "Very thin oxygen atmosphere; unbreathable.",
         "Fractured icy terrain. A major target for investigating potentially habitable ocean environments.", "~ -160 C, varying strongly by location", .0094),
    moon("Ganymede", "Jupiter", 1.4819e23, 2634.1, 1070400, 7.15455,
         "Rock and water ice, likely subsurface ocean layers and an iron-rich core.",
         "Very thin oxygen-bearing atmosphere.",
         "Largest moon in the solar system, wider than Mercury; has an intrinsic magnetic field.", "~ -163 C representative surface", .0013),
    moon("Callisto", "Jupiter", 1.0759e23, 2410.3, 1882700, 16.6890,
         "Rock and water ice; a buried salty ocean is possible.", "Very thin carbon dioxide exosphere.",
         "Ancient, densely cratered terrain including the large multi-ring Valhalla structure.", "~ -139 C representative surface", .0074),
    moon("Mimas", "Saturn", 3.7493e19, 198.2, 185539, .94242,
         "Mostly water ice with some rock; interior ocean interpretation remains under study.", "No substantial atmosphere.",
         "The huge Herschel crater dominates its appearance.", "~ -209 C", .0196),
    moon("Enceladus", "Saturn", 1.0802e20, 252.1, 238042, 1.37022,
         "Bright ice shell, global salty ocean and a rocky interior.", "Transient water-vapor plume environment.",
         "South-polar jets eject water and ice; plume material feeds Saturn's E ring.", "~ -201 C; warmer south-polar fractures", .0047),
    moon("Tethys", "Saturn", 6.1745e20, 531.1, 294672, 1.88780,
         "Water-ice-dominated interior with a small rocky fraction.", "No substantial atmosphere.",
         "Odysseus impact basin and the enormous Ithaca Chasma fracture system.", "~ -187 C", .0001),
    moon("Dione", "Saturn", 1.0955e21, 561.4, 377415, 2.73692,
         "Water ice surrounding a substantial rocky interior.", "Very tenuous oxygen exosphere.",
         "Bright ice cliffs and ancient craters; evidence suggests possible past internal activity.", "~ -186 C", .0022),
    moon("Rhea", "Saturn", 2.3065e21, 763.8, 527068, 4.51821,
         "Mostly water ice mixed with rock.", "Extremely thin oxygen and carbon dioxide exosphere.",
         "Saturn's second-largest moon; a heavily cratered world with bright fractures.", "~ -174 to -220 C", .0010),
    moon("Titan", "Saturn", 1.3452e23, 2574.7, 1221870, 15.9454,
         "Icy crust, likely internal water ocean and rocky interior; organic surface material.",
         "Dense nitrogen atmosphere with methane and organic haze; ~1.5 bar at surface.",
         "Methane/ethane lakes and seas, dunes and a methane weather cycle. Huygens landed in 2005.", "~ -179 C surface", .0288),
    moon("Hyperion", "Saturn", 5.619e18, 135.0, 1481000, 21.2766,
         "Very porous, low-density ice and dark rocky material.", "No substantial atmosphere.",
         "Sponge-like irregular shape and chaotic tumbling; rotation has no single stable period.", "~ -180 C", .1230, locked=False),
    moon("Iapetus", "Saturn", 1.8056e21, 734.5, 3560820, 79.3215,
         "Mostly water ice with rock and a dark surface coating on one hemisphere.", "No substantial atmosphere.",
         "A dramatic dark/bright contrast and an enormous equatorial ridge.", "~ -143 to -223 C", .0286),
    moon("Phoebe", "Saturn", 8.292e18, 106.5, 12952000, 550.48,
         "Ice and rock with dark, carbon-bearing surface material.", "No substantial atmosphere.",
         "Captured, irregular retrograde satellite. Spin period is about 9.3 hours.", "~ -198 C", .1634, retrograde=True, locked=False),
    moon("Miranda", "Uranus", 6.59e19, 235.8, 129390, 1.41348,
         "Water ice and rocky material.", "No substantial atmosphere.",
         "Patchwork terrain, deep canyons and huge cliffs such as Verona Rupes.", "~ -187 C", .0013),
    moon("Ariel", "Uranus", 1.353e21, 578.9, 191020, 2.52038,
         "Water ice mixed with rock; carbon dioxide ice appears on the surface.", "No substantial atmosphere.",
         "Bright surface cut by long valleys and signs of ancient resurfacing.", "~ -213 C", .0012),
    moon("Umbriel", "Uranus", 1.172e21, 584.7, 266300, 4.14418,
         "Water ice and rock with a dark surface layer.", "No substantial atmosphere.",
         "Dark, ancient cratered terrain with a conspicuous bright ring near the crater Wunda.", "~ -214 C", .0039),
    moon("Titania", "Uranus", 3.527e21, 788.9, 435910, 8.70587,
         "Rock and water ice; possible internal ocean is unconfirmed.", "No substantial atmosphere detected.",
         "Largest Uranian moon; long fault valleys suggest expansion and past internal activity.", "~ -203 C", .0011),
    moon("Oberon", "Uranus", 3.014e21, 761.4, 583520, 13.4632,
         "Water ice and rock, with dark material in some crater floors.", "No substantial atmosphere.",
         "Outermost of Uranus's five major moons; heavily cratered with large fault scarps.", "~ -203 C", .0014),
    moon("Proteus", "Neptune", 4.4e19, 210.0, 117647, 1.12232,
         "Dark ice/rock mixture; mass and interior are poorly constrained.", "No substantial atmosphere.",
         "Irregular inner moon; large Pharos impact crater. Mass is a rough estimate.", "~ -223 C", .0005, estimated=True),
    moon("Triton", "Neptune", 2.1390e22, 1353.4, 354759, 5.87685,
         "Rock-rich interior, water-ice mantle and nitrogen/methane/carbon monoxide surface ices.",
         "Extremely thin nitrogen atmosphere with traces of methane.",
         "Large retrograde moon, probably captured; Voyager 2 observed active plumes in 1989.", "~ -235 C", .000016, retrograde=True),
    moon("Nereid", "Neptune", 3.1e19, 170.0, 5513818, 360.136,
         "Water ice and dark material; interior and mass are poorly known.", "No substantial atmosphere.",
         "Highly eccentric orbit. Spin is roughly 11.6 hours; its mass is only an estimate.", "~ -223 C", .7507, locked=False, estimated=True),
]

MOONS.append(moon("Charon", "Pluto", 1.586e21, 606.0, 19596, 6.38723,
                  "Rock and water ice, with ammonia-bearing compounds on parts of the surface.",
                  "No substantial atmosphere detected.",
                  "Pluto's largest moon; mutually tidally locked. The pair orbits a shared center of mass outside Pluto.",
                  "~ -220 C representative surface", .0002))

BODIES = {b.name.lower(): b for b in [SUN, *PLANETS, *DWARF_PLANETS, *MOONS]}
ALIASES = {"sol": "sun", "luna": "moon", "terra": "earth", "the moon": "moon"}


def lookup(name):
    key = name.strip().lower().strip('\"\'')
    return BODIES.get(ALIASES.get(key, key))


def satellites(name):
    return [b for b in MOONS if b.parent.lower() == name.lower()]


# NASA/JPL Table 1: a, e, I, L, longitude of perihelion, longitude of node.
# Each tuple contains J2000 values followed by their rates per Julian century.
# Earth uses the Earth-Moon barycenter as an educational approximation.
ELEMENTS = {
    "Mercury": ((.38709927,.20563593,7.00497902,252.25032350,77.45779628,48.33076593),
                (.00000037,.00001906,-.00594749,149472.67411175,.16047689,-.12534081)),
    "Venus": ((.72333566,.00677672,3.39467605,181.97909950,131.60246718,76.67984255),
              (.00000390,-.00004107,-.00078890,58517.81538729,.00268329,-.27769418)),
    "Earth": ((1.00000261,.01671123,-.00001531,100.46457166,102.93768193,0),
              (.00000562,-.00004392,-.01294668,35999.37244981,.32327364,0)),
    "Mars": ((1.52371034,.09339410,1.84969142,-4.55343205,-23.94362959,49.55953891),
             (.00001847,.00007882,-.00813131,19140.30268499,.44441088,-.29257343)),
    "Jupiter": ((5.202887,.04838624,1.30439695,34.39644051,14.72847983,100.47390909),
                (-.00011607,-.00013253,-.00183714,3034.74612775,.21252668,.20469106)),
    "Saturn": ((9.53667594,.05386179,2.48599187,49.95424423,92.59887831,113.66242448),
               (-.00125060,-.00050991,.00193609,1222.49362201,-.41897216,-.28867794)),
    "Uranus": ((19.18916464,.04725744,.77263783,313.23810451,170.95427630,74.01692503),
               (-.00196176,-.00004397,-.00242939,428.48202785,.40805281,.04240589)),
    "Neptune": ((30.06992276,.00859048,1.77004347,-55.12002969,44.96476227,131.78422574),
                (.00026291,.00005105,.00035372,218.45945325,-.32241464,-.00508664)),
}
