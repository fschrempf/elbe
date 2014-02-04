#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
from optparse import OptionParser
from treeutils import etree

import elbepack
from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version

def run_command(argv):

    oparser = OptionParser(usage="usage: %prog create-target-rfs [options] <xmlfile>")
    oparser.add_option( "-t", "--target", dest="target",
                         help="directoryname of target" )
    oparser.add_option( "-d", "--debug", dest="debug", default=False,
                         help="additional debug output" )
    oparser.add_option( "-b", "--buildchroot", dest="buildchroot", default=False, action = 'store_true',
                         help="copy kernel to /opt/elbe" )
    oparser.add_option( "-o", "--output", dest="output",
                         help="name of logfile" )
    oparser.add_option("--buildtype", dest="buildtype",
            help="Override the buildtype" )

    (opt, args) = oparser.parse_args(argv)
    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(1)

    if not opt.target:
        print "Missing target (-t)"
        #sys.exit(1)

    if not validate_xml(args[0]):
        print "xml validation failed. Bailing out"
        sys.exit(20)

    xml = etree(args[0] )
    prj = xml.node("/project")
    tgt = xml.node("/target")

    target = os.path.abspath(opt.target)

    if opt.buildtype:
        buildtype = opt.buildtype
    elif xml.has( "project/buildtype" ):
        buildtype = xml.text( "/project/buildtype" )
    else:
        buildtype = "nodefaults"
    defs = ElbeDefaults(buildtype)

    os.system("rm -rf /target")
    os.system("mkdir -p /target")
    os.system("rm -f /opt/elbe/filelist")

    # create filelists describing the content of the target rfs
    if tgt.has("tighten"):
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1.list@' /opt/elbe/pkg-list | sh >> /opt/elbe/filelist")
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1.conffiles@' /opt/elbe/pkg-list | sh >> /opt/elbe/filelist")

    elif tgt.has("diet"):

        arch = xml.text("project/buildimage/arch", default=defs, key="arch")
        os.system("apt-rdepends `cat /opt/elbe/pkg-list` | grep -v \"^ \" | uniq >/opt/elbe/allpkg-list")
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1.list@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist")
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1.conffiles@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist")
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1:%s .list@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist" %
                arch)
        os.system("sed 's@^\(.*\)@cat /var/lib/dpkg/info/\\1:%s.conffiles@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist" %
                arch)
    else:
        os.system("ls -A1 / | grep -v target | grep -v proc | grep -v sys | xargs find | grep -v \"^opt/elbe\" >> /opt/elbe/filelist")

    # create target rfs
    os.chdir("/")
    os.system("rsync -a --files-from=/opt/elbe/filelist / /target")

    os.system("mkdir /target/proc")
    os.system("mkdir /target/sys")

    if tgt.has("setsel"):
        os.system("mount -o bind /proc /target/proc")
        os.system("mount -o bind /sys /target/sys")

        os.system("chroot /target dpkg --clear-selections")
        os.system("chroot /target dpkg --set-selections </opt/elbe/pkg-selections")
        os.system("chroot /target dpkg --purge -a")

        os.system("umount /target/proc")
        os.system("umount /target/sys")


    os.system("rm -f /etc/elbe_version")

    os.system("echo %s %s >> /etc/elbe_version" %(prj.text("name"), prj.text("version")))
    os.system("echo this RFS was generated by elbe %s >> /etc/elbe_version" % (elbe_version))
    os.system("echo `date` >> /etc/elbe_version")

    os.system("rm -f /opt/elbe/dump.log")

    if xml.has("archive"):
        os.system("elbe dump --name \"%s\" --output /opt/elbe/elbe-report.txt "
            "--validation /opt/elbe/validation.txt --target /target "
            "--finetuning /opt/elbe/finetuning.sh --archive /opt/elbe/archive.tar.bz2 "
            "--kinitrd \"%s\" /opt/elbe/source.xml  >> /opt/elbe/dump.log 2>&1" %
            (prj.text("name"), prj.text("buildimage/kinitrd")))

    else:
        os.system("elbe dump --name \"%s\" --output /opt/elbe/elbe-report.txt "
            "--validation /opt/elbe/validation.txt --target /target "
            "--finetuning /opt/elbe/finetuning.sh --kinitrd \"%s\" /opt/elbe/source.xml "
            ">> /opt/elbe/dump.log 2>&1" % (prj.text("name"),
                prj.text("buildimage/kinitrd")))

    os.system("rm -rf /opt/elbe/licence.txt")

    os.system("find /usr/share/doc -name copyright -exec "
            "/opt/elbe/print_licence.sh {} \; >> /opt/elbe/licence.txt")

    # create target images and copy the rfs into them
    os.system("/opt/elbe/part-target.sh >> /opt/elbe/elbe-report.txt 2>&1")

    if xml.has("target/package/tar"):
        os.system("tar cf /opt/elbe/target.tar -C /target .")
        os.system("echo /opt/elbe/target.tar >> /opt/elbe/files-to-extract")

    if xml.has("target/package/cpio"):
        cpio_name = xml.text("target/package/cpio/name")
        os.chdir("/target")
        os.system("find . -print | cpio -ov -H newc >/opt/elbe/%s" % cpio_name)
        os.system("echo /opt/elbe/%s >> /opt/elbe/files-to-extract" % cpio_name)
        os.chdir("/")

    os.system("echo '' >> /opt/elbe/elbe-report.txt")
    os.system("echo '' >> /opt/elbe/elbe-report.txt")
    os.system("echo 'output of dump.py' >> /opt/elbe/elbe-report.txt")
    os.system("echo '-----------------' >> /opt/elbe/elbe-report.txt")
    os.system("cat /opt/elbe/dump.log   >> /opt/elbe/elbe-report.txt")

    os.system("echo '' >> /opt/elbe/elbe-report.txt")
    os.system("echo '' >> /opt/elbe/elbe-report.txt")
    os.system("echo built with elbe v%s >> /opt/elbe/elbe-report.txt" % (elbe_version))

    os.system("echo /opt/elbe/licence.txt >> /opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/elbe-report.txt >> /opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/source.xml >> /opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/validation.txt >> /opt/elbe/files-to-extract")

    if opt.debug:
        os.system("echo /var/log/syslog >> /opt/elbe/files-to-extract")

    if not opt.buildchroot:
        if xml.text("project/buildimage/arch", default=defs, key="arch") == "armel":
            os.system("cp -L /boot/vmlinuz /opt/elbe/vmkernel")
            os.system("cp -L /boot/initrd.img /opt/elbe/vminitrd")
        elif xml.text("project/buildimage/arch", default=defs, key="arch") == "powerpc":
            os.system("cp -L /boot/vmlinux /opt/elbe/vmkernel")
            os.system("cp -L /boot/initrd.img /opt/elbe/vminitrd")
        else:
            os.system("cp -L /vmlinuz /opt/elbe/vmkernel")
            os.system("cp -L /initrd.img /opt/elbe/vminitrd")

if __name__ == "__main__":
    run_command(sys.argv[1:])
