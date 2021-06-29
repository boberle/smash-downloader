import subprocess
import os

f = 'test/truc.brstm'
#f = 'all/129_halo_2/18535_cairo_suite.brstm'
proc = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'null', '-'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(proc.returncode)
print("STDOUT", proc.stdout)
print("STDERR", proc.stderr)
input('foo')

counter = 0
for root, dirnames, filenames in os.walk('all'):
    for filename in filenames:
        if filename.endswith('.brstm'):
            path = os.path.join(root, filename)
            counter += 1
            if counter % 500 == 0:
                print(counter)
            proc = subprocess.run(
                ['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0 or proc.stdout or proc.stderr:
                print("ERROR:", path)
                print(proc.stdout)
                print(proc.stderr)

