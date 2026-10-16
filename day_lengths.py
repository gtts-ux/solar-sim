"""Mean solar days versus sidereal spin periods, using catalogue approximations."""
from catalog import SUN, lookup


def spin_hours(body):
    return body.rotation or {'Phoebe':9.3,'Nereid':11.6}.get(body.name)


def solar_hours(body):
    if body is SUN or body.kind=='Artificial satellite':
        return None
    spin=spin_hours(body)
    if not spin:
        return None
    primary=body if body.parent=='Sun' else lookup(body.parent)
    year=primary.period*24
    frequency=1/spin-1/year
    return 1/abs(frequency) if frequency else None


def day_label(body):
    solar=solar_hours(body)
    if solar is None:
        return 'Not defined for a star' if body is SUN else 'No stable solar day' if body.name=='Hyperion' else 'Not applicable'
    return f'~{solar:.2f} hours ({solar/24:.3f} Earth days)'


def day_info(body):
    if body.kind=='Artificial satellite':
        return f'{body.name.upper()} / DAY LENGTH\n\nSpacecraft have no planetary solar day.\nNominal orbital period: {body.period*1440:.1f} minutes.\nUse /day {body.parent.lower()} for the parent world.'
    spin=spin_hours(body)
    rotation=(f'{abs(spin):,.4f} hours ({abs(spin)/24:.4f} Earth days)'+(' / retrograde' if spin<0 else '')) if spin else 'Chaotic rotation; no stable period'
    return (f'{body.name.upper()} / DAY LENGTH\n\n'
            f'  Mean solar day       {day_label(body)}\n'
            f'  Sidereal rotation    {rotation}\n\n'
            'A solar day is noon-to-noon (the average sunrise-to-sunrise cycle).\n'
            'Sidereal rotation is one spin relative to distant stars.\n'
            'Values are approximate means, not daylight hours at a particular location.\n'
            'They omit seasonal, obliquity and eccentric-orbit variations.\n'
            'For moons, the solar-day estimate uses the parent world\'s year.\n'
            'The Sun rotates at different rates with latitude; it has no solar day on itself.')
