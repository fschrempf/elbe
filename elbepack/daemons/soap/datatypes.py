# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from spyne.model.complex import ComplexModel
from spyne.model.primitive import Unicode, DateTime


class SoapProject (ComplexModel):
    __namespace__ = 'soap'

    builddir = Unicode()
    name = Unicode()
    version = Unicode()
    status = Unicode()
    edit = DateTime()

    def __init__(self, prj):
        self.builddir = prj.builddir
        self.name = prj.name
        self.version = prj.version
        self.status = prj.status
        self.edit = prj.edit
        ComplexModel.__init__(self)


class SoapFile (ComplexModel):
    __namespace__ = 'soap'

    name = Unicode()
    description = Unicode()

    def __init__(self, fi):
        self.name = fi.name
        self.description = fi.description
        ComplexModel.__init__(self)
