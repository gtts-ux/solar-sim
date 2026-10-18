"""Presentation of the fictional Interstellar catalogue; geometry is a schematic."""
SOURCE = 'Fictional Interstellar model; invented orbital layout/periods, no GR integration'
NOTICE = ('INTERSTELLAR / fictional film system\n\n'
          'Gargantua / Miller / Mann / Edmunds\n'
          'A separate catalogue inspired by Interstellar (2014).\n'
          'Distances, radii, planetary masses and animation periods are model choices,\n'
          'not canonical measurements or real astronomical discoveries.\n'
          'The map groups the three worlds around Gargantua schematically; it does\n'
          'not establish their physical host-star arrangement.\n'
          'UTC controls the animation; relativity and film time dilation are not integrated.\n\n'
          '/planet lists worlds  /gargantua opens the black hole\n'
          '/miller  /mann  /edmunds opens profiles or focuses their orbit\n'
          '/orbit opens the map; Left/Right zooms in orbit mode\n'
          '/compare miller mann  /sources\n'
          '/interstellar exit returns to normal planets. /dwarf switches to dwarfs.')


def describe(body, date, position):
    planet = bool(body.parent)
    lines = [body.name.upper()+' / '+body.kind, '', 'FICTIONAL MODEL / Interstellar (2014)',
             '  Primary on this map  '+(body.parent or 'Local schematic origin'),
             f'  Model mass           {body.mass:.6g} kg'+(' (invented placeholder)' if planet else ' (~100 million Suns, film-science interpretation)'),
             f'  Model radius         {body.radius:,.1f} km'+(' (invented placeholder)' if planet else ' (GM/c^2 reference scale; not a solid surface)'),
             f'  Model diameter       {2*body.radius:,.1f} km (drawing reference)',
             f'  Model orbital radius {body.orbit:,.0f} km' if planet else '  Horizon / spin       Spinning Kerr black hole in the film; no exact horizon modeled',
             f'  Animation cycle      {body.period:g} simulation days (invented)' if planet else '  Surface / solar day  Not applicable to a black hole',
             '  Solar day / rotation Not specified; no numeric day length invented' if planet else '  Accretion material   Luminous gas outside the hole in the film',
             '  Moons / rings        Not specified; none included in this mod' if planet else '  Worlds on this map   Miller, Mann, Edmunds (schematic grouping)',
             '  Spacecraft           No spacecraft orbits included; Endurance is part of the story',
             '', 'ENVIRONMENT / film-inspired description', '  '+body.temperature,
             '', 'COMPOSITION', '  '+body.composition, '', 'ATMOSPHERE', '  '+body.atmosphere,
             '', 'STORY / MODEL NOTES', '  '+body.features,
             '', 'POSITION / fictional Gargantua-centered drawing coordinates',
             f'  UTC reference        {date:%Y-%m-%d %H:%M:%S}',
             '  X / Y / Z (km)       '+' / '.join(f'{p:,.1f}' for p in position(body)),
             '  '+SOURCE, '',
             'No measured surface gravity, density or relativistic flight times are inferred.',
             '/orbit  /compare miller mann  /sources  /interstellar exit']
    return '\n'.join(lines)
