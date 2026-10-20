"""Arrow-menu forms for the format-2 mod maker."""
import shlex

NUMERIC=(('mass','Mass (kg)'),('radius','Radius (km)'),('orbit','Orbital radius (km)'),
         ('period','Orbital period (Earth days)'),('rotation','Rotation / day (hours)'),
         ('eccentricity','Eccentricity (0 to <0.95)'),('inclination','Inclination (degrees)'),
         ('node','Ascending node (degrees)'),('periapsis','Periapsis (degrees)'),('phase','Initial phase (degrees)'))


def items(sim,context):
    from navigation import Item
    builder=sim.builder
    def edit(label,action,value='',detail=''):
        return Item(label,detail or 'Type a value; Enter saves; Esc cancels. First typing replaces the selected value.',edit=action,value=value)
    def command(label,args,detail=''):
        return Item(label,detail,('/builder '+args,),stay=True)
    try:state=builder.state
    except (ValueError,OSError) as error:
        return (edit('Start a fresh draft',('new',),detail='The damaged draft will be backed up first. '+str(error)),
                Item('Manual JSON tutorial',str(error),('/mod tutorial',)))
    if context=='projects':
        projects=builder.projects()
        return tuple(command(name,'load '+shlex.quote(name),'Resume this saved draft/project; current work is backed up.') for name in projects) or (Item('No saved projects yet','Create a mod, then export its project folder.'),)
    if context=='home':
        entries=[]
        if state is not None:
            p=state['package'];bodies=p['bodies']
            entries=[Item('Mod details',p['name']+' / '+p['id']+' / v'+p['version'],builder='details'),
                     edit('Project notes',('set','project','notes'),state['notes'].replace('\n','\\n'),'Notes included in the README. Type \\n for a paragraph break.')]
            entries.extend(Item(b['name']+' / '+b['kind'],'Parent: '+(b['parent'] or 'System center; one central star per mod.'),builder='body:'+str(i)) for i,b in enumerate(bodies,1))
            if not bodies:entries.append(edit('Add star',('add','Star',''),detail='Name the central star. Edit the starter model values afterward.'))
            else:
                entries.append(edit('Add planet',('add','Planet',''),detail='Name a planet around '+bodies[0]['name']+'.'))
                entries.append(edit('Add dwarf planet',('add','Dwarf planet',''),detail='Name a dwarf planet around '+bodies[0]['name']+'.'))
            entries += [command('Validate draft','validate','Check the same schema used by the public mod installer.'),
                        command('Export project folder','export','Create solar-mod.json, README and publishing instructions in a new folder. Existing exports stay intact.')]
        return tuple(entries+[edit('New mod...',('new',),detail='Name a new fictional draft. Previous work is backed up.'),
                              Item('Open saved project','Resume an exported project or an earlier saved draft.',builder='projects'),
                              Item('Manual JSON tutorial','Keep using the existing file-based mod workflow.',('/mod tutorial',))])
    if state is None:return items(sim,'home')
    if context=='details':
        p=state['package']
        entries=[edit(label,('set','mod',field),p[field],hint) for field,label,hint in (
            ('name','Mod name','Display name, up to 64 characters.'),
            ('id','Mod ID','Unique lowercase letters/digits and hyphens; used for installation and the export folder.'),
            ('description','Description','Describe the system and its model.'),
            ('version','Version','Three numbers, for example 1.0.0. Increase before publishing an update.'))]
        return tuple(entries+[command('System type: '+('Fictional' if p['fictional'] else 'Real / sourced'),
                                      'set mod fictional '+('false' if p['fictional'] else 'true'),'Toggle type. Real systems need HTTPS sources before export.'),
                              edit('Source links',('set','mod','sources'),'; '.join(p['sources']),'HTTPS URLs separated by semicolons.')])
    if context.startswith('body:'):
        index=context.split(':',1)[1]
        try:b=builder.body(index)
        except ValueError:return items(sim,'home')
        entries=[edit('Name',('set','body',index,'name'),b['name'],'Renaming also updates the parent name in its moons.'),Item('Type: '+b['kind'],'Object type in this mod.')]
        if b['parent']:
            if b['kind']=='Moon':
                parents=tuple(command(p['name'],'set body '+index+' parent '+shlex.quote(p['name']),'Move this moon; invalid cycles are rejected.') for p in state['package']['bodies'] if p['kind'] in ('Planet','Dwarf planet','Moon') and p['name']!=b['name'])
                entries.append(Item('Parent: '+b['parent'],'Choose the parent planet or moon.',children=parents))
            else:entries.append(Item('Parent: '+b['parent'],'Planets orbit the central body.'))
        for field,label in NUMERIC:
            if not b['parent'] and field in ('orbit','period','eccentricity','inclination','node','periapsis','phase'):continue
            entries.append(edit(label,('set','body',index,field),str(b.get(field,0)),label+'. Scientific notation such as 5.972e24 is accepted.'))
        for field,label in (('temperature','Temperature'),('composition','Composition'),('atmosphere','Atmosphere'),('features','Body notes')):
            entries.append(edit(label,('set','body',index,field),b[field],'Describe '+label.lower()+'. Included in the body profile.'))
        colors=('Red','Green','Yellow','Blue','Magenta','Cyan','White')
        entries.append(Item('Map colour: '+colors[b['color']-1],'Choose a map marker colour.',children=tuple(command(label,'set body '+index+' color '+str(i)) for i,label in enumerate(colors,1))))
        entries.append(edit('Aliases',('set','body',index,'aliases'),'; '.join(b.get('aliases',[])),'Alternative names separated by semicolons.'))
        for field,label in (('estimated_mass','Mass is an estimate'),('estimated_radius','Radius is an estimate')):
            entries.append(command(label+': '+('Yes' if b.get(field,True) else 'No'),
                                   'set body '+index+' '+field+' '+('false' if b.get(field,True) else 'true'),'Starter values are estimates; supply your own numbers before changing this.'))
        if b['kind'] in ('Planet','Dwarf planet','Moon'):
            entries.append(edit('Add moon',('add','Moon',b['name']),detail='Name a moon orbiting '+b['name']+'.'))
        entries.append(command('Remove body and its moons','delete '+index,'Remove '+b['name']+' and its descendants from the draft. Exported projects stay intact.'))
        return tuple(entries)
    return items(sim,'home')


def submit(builder,action,value):
    if action[0]=='new':return builder.new(value),None
    if action[0]=='add':
        index=builder.add(action[1],value,action[2] or None)
        return 'Added '+builder.body(index)['name']+'. Draft saved.',index
    if action[:2]==('set','body'):return builder.set('body',action[3],value,action[2]),None
    if action[0]=='set':return builder.set(action[1],action[2],value),None
    raise ValueError('Unknown builder action.')
