# -*- coding: utf-8 -*-
# Author: Milan Nikolic <gen2brain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import ctypes as C

from PyQt4.QtCore import SIGNAL
from PyQt4.QtOpenGL import QGLFormat

from SDL import *

try:
    from m64py.core.defs import *
    from m64py.utils import log
except ImportError, err:
    sys.stderr.write("Error: Can't import m64py modules%s%s%s" % (
        os.linesep, str(err), os.linesep))
    sys.exit(1)

try:
    if not SDL_WasInit(SDL_INIT_VIDEO):
        SDL_InitSubSystem(SDL_INIT_VIDEO)
    MODES = [(mode.w, mode.h) for mode in SDL_ListModes(
        None, SDL_FULLSCREEN|SDL_HWSURFACE)]
    SDL_QuitSubSystem(SDL_INIT_VIDEO)
except Exception, err:
    log.warn(str(err))
    MODES = [(1920, 1440), (1600, 1200), (1400, 1050),
            (1280, 960), (1152, 864), (1024, 768),
            (800, 600), (640, 480), (320, 240)]

class Video():
    """Mupen64Plus video extension"""

    def __init__(self):
        """Constructor."""
        self.parent = None
        self.widget = None
        self.glcontext = None

    def set_widget(self, parent):
        """Sets GL widget."""
        self.parent = parent
        self.widget = self.parent.glwidget

    def init(self):
        """Initialize GL context."""
        if not self.glcontext:
            self.glformat = QGLFormat()
            self.glcontext = self.widget.context()
            self.glcontext.setFormat(self.glformat)
            self.glcontext.create()
        return M64ERR_SUCCESS

    def quit(self):
        """Shuts down the video system."""
        if self.glcontext:
            self.glcontext.doneCurrent()
        return M64ERR_SUCCESS

    def list_fullscreen_modes(self, size_array, num_sizes):
        """Enumerates the available resolutions
        for fullscreen video modes."""
        num_sizes.contents.value = len(MODES)
        for num, mode in enumerate(MODES):
            width, height = mode
            size_array[num].uiWidth = width
            size_array[num].uiHeight = height
        return M64ERR_SUCCESS

    def set_video_mode(self, width, height, bits, mode):
        """Creates a rendering window."""
        self.glcontext.makeCurrent()
        if self.glcontext.isValid():
            return M64ERR_SUCCESS
        else:
            return M64ERR_SYSTEM_FAIL

    def set_caption(self, title):
        """Sets the caption text of the
        emulator rendering window. """
        title = "M64Py :: %s" % title
        self.parent.emit(
                SIGNAL("set_caption(PyQt_PyObject)"), title)
        return M64ERR_SUCCESS

    def toggle_fs(self):
        """Toggles between fullscreen and
        windowed rendering modes. """
        self.widget.emit(SIGNAL("toggle_fs()"))
        return M64ERR_SUCCESS

    def gl_get_proc(self, proc):
        """Used to get a pointer to
        an OpenGL extension function."""
        addr = self.glcontext.getProcAddress(proc)
        if addr is not None:
            return addr.__int__()
        else:
            log.warn("VidExtFuncGLGetProc: '%s'" % proc)

    def gl_set_attr(self, attr, value):
        """Sets OpenGL attributes."""
        attr_map = {
                M64P_GL_DOUBLEBUFFER: self.glformat.setDoubleBuffer,
                M64P_GL_BUFFER_SIZE: self.glformat.setDepthBufferSize,
                M64P_GL_DEPTH_SIZE: self.glformat.setDepth,
                M64P_GL_RED_SIZE: self.glformat.setRedBufferSize,
                M64P_GL_GREEN_SIZE: self.glformat.setGreenBufferSize,
                M64P_GL_BLUE_SIZE: self.glformat.setBlueBufferSize,
                M64P_GL_ALPHA_SIZE: self.glformat.setAlphaBufferSize,
                M64P_GL_SWAP_CONTROL: self.glformat.setSwapInterval,
                M64P_GL_MULTISAMPLEBUFFERS: self.glformat.setSampleBuffers,
                M64P_GL_MULTISAMPLESAMPLES: self.glformat.setSamples
        }
        set_attr = attr_map[attr]
        set_attr(value)
        return M64ERR_SUCCESS

    def gl_get_attr(self, attr, value):
        """Gets OpenGL attributes."""
        attr_map = {
                M64P_GL_DOUBLEBUFFER: self.glformat.doubleBuffer,
                M64P_GL_BUFFER_SIZE: self.glformat.depthBufferSize,
                M64P_GL_DEPTH_SIZE: self.glformat.depth,
                M64P_GL_RED_SIZE: self.glformat.redBufferSize,
                M64P_GL_GREEN_SIZE: self.glformat.greenBufferSize,
                M64P_GL_BLUE_SIZE: self.glformat.blueBufferSize,
                M64P_GL_ALPHA_SIZE: self.glformat.alphaBufferSize,
                M64P_GL_SWAP_CONTROL: self.glformat.swapInterval,
                M64P_GL_MULTISAMPLEBUFFERS: self.glformat.sampleBuffers,
                M64P_GL_MULTISAMPLESAMPLES: self.glformat.samples
        }
        get_attr = attr_map[attr]
        new_value = int(get_attr())
        if new_value == value.contents.value:
            return M64ERR_SUCCESS
        else:
            return M64ERR_SYSTEM_FAIL

    def gl_swap_buf(self):
        """Swaps the front/back buffers after
        rendering an output video frame. """
        self.widget.swapBuffers()
        return M64ERR_SUCCESS

m64p_error = C.c_int
m64p_GLattr = C.c_int

class m64p_2d_size(C.Structure):
    _fields_ = [
        ('uiWidth', C.c_uint),
        ('uiHeight', C.c_uint)
        ]

FuncInit =C.CFUNCTYPE(m64p_error)
FuncQuit = C.CFUNCTYPE(m64p_error)
FuncListModes = C.CFUNCTYPE(m64p_error, C.POINTER(m64p_2d_size), C.POINTER(C.c_int))
FuncSetMode = C.CFUNCTYPE(m64p_error, C.c_int, C.c_int, C.c_int, C.c_int)
FuncGLGetProc = C.CFUNCTYPE(C.c_void_p, C.c_char_p)
FuncGLSetAttr = C.CFUNCTYPE(m64p_error, m64p_GLattr, C.c_int)
FuncGLGetAttr = C.CFUNCTYPE(m64p_error, m64p_GLattr, C.POINTER(C.c_int))
FuncGLSwapBuf = C.CFUNCTYPE(m64p_error)
FuncSetCaption = C.CFUNCTYPE(m64p_error, C.c_char_p)
FuncToggleFS= C.CFUNCTYPE(m64p_error)

class m64p_video_extension_functions(C.Structure):
    _fields_ = [
        ('Functions', C.c_uint),
        ('VidExtFuncInit', FuncInit),
        ('VidExtFuncQuit', FuncQuit),
        ('VidExtFuncListModes', FuncListModes),
        ('VidExtFuncSetMode', FuncSetMode),
        ('VidExtFuncGLGetProc', FuncGLGetProc),
        ('VidExtFuncGLSetAttr', FuncGLSetAttr),
        ('VidExtFuncGLGetAttr', FuncGLGetAttr),
        ('VidExtFuncGLSwapBuf', FuncGLSwapBuf),
        ('VidExtFuncSetCaption', FuncSetCaption),
        ('VidExtFuncToggleFS', FuncToggleFS),
    ]

video = Video()
vidext = m64p_video_extension_functions()
vidext.Functions = 10
vidext.VidExtFuncInit = FuncInit(video.init)
vidext.VidExtFuncQuit = FuncQuit(video.quit)
vidext.VidExtFuncListModes = FuncListModes(video.list_fullscreen_modes)
vidext.VidExtFuncSetMode = FuncSetMode(video.set_video_mode)
vidext.VidExtFuncGLGetProc = FuncGLGetProc(video.gl_get_proc)
vidext.VidExtFuncGLSetAttr = FuncGLSetAttr(video.gl_set_attr)
vidext.VidExtFuncGLGetAttr = FuncGLGetAttr(video.gl_get_attr)
vidext.VidExtFuncGLSwapBuf = FuncGLSwapBuf(video.gl_swap_buf)
vidext.VidExtFuncSetCaption = FuncSetCaption(video.set_caption)
vidext.VidExtFuncToggleFS = FuncToggleFS(video.toggle_fs)
