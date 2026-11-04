"""Rebuild the published localization from inspectable text exports."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from pylocres import LocresFile,Namespace,Entry

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repak',required=True,help='Path to repak v0.2.3')
    parser.add_argument('--output',default='build',help='New output directory')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=Path(args.output).resolve()
    if output.exists():raise SystemExit('Output directory already exists; choose a new directory.')
    manifest=json.loads((root/'CONTENTS.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    for resource in manifest['localization_resources']:
        loc=LocresFile();count=0
        for part in resource['parts']:
            file=(root/part['path']).resolve()
            if not file.is_relative_to(root) or digest(file)!=part['sha256']:raise ValueError('Text export checksum mismatch: '+part['path'])
            data=json.loads(file.read_text(encoding='utf-8'))
            if data['resource']!=resource['resource']:raise ValueError('Resource mismatch')
            namespace=data['namespace']
            if namespace not in loc:loc.add(Namespace(namespace))
            for row in data['entries']:
                loc[namespace].add(Entry(row['key'],row['translation'],row['source_crc32']));count+=1
        if count!=resource['entries']:raise ValueError('Entry count mismatch')
        relative=Path(resource['path_in_pak'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid payload path')
        target=output/'payload'/relative;target.parent.mkdir(parents=True,exist_ok=True);loc.write(target)
        if digest(target)!=resource['sha256']:raise ValueError('Localization checksum mismatch: '+resource['resource'])
    pak=output/'ZZ_RussianExtra_P.pak'
    subprocess.run([args.repak,'pack','--version','V11',str(output/'payload'),str(pak)],check=True)
    indexed={row['name']:row for row in manifest['files']}
    # Container metadata ordering may differ; verify every unpacked member byte-for-byte.
    unpacked=output/'verified_unpack'
    subprocess.run([args.repak,'unpack','--output',str(unpacked),str(pak)],check=True)
    expected={r['path_in_pak']:r['sha256'] for r in manifest['localization_resources']}
    actual={str(p.relative_to(unpacked)).replace('\\','/'):digest(p) for p in unpacked.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Unpacked localization files differ from the published package')
    for ext in ('utoc','ucas'):
        name='ZZ_RussianExtra_P.'+ext;source=(root/indexed[name]['path']).resolve()
        if not source.is_relative_to(root) or digest(source)!=indexed[name]['sha256']:raise ValueError('Container checksum mismatch: '+name)
        shutil.copy2(source,output/name)
    print('All three localization tables match the published package byte-for-byte. Container companions verified. No game files were installed.')

if __name__=='__main__':main()
