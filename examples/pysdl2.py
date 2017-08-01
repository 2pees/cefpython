"""
 Simple SDL2 / cefpython3 example.

 Only handles mouse events but could be extended to handle others.

 Requires pysdl2 (and SDL2 library).

 Install instructions.
 
 1. Install SDL libraries for your OS, e.g. for Fedora:

   dnf install SDL2 SDL2_ttf SDL2_image SDL2_gfx SDL2_mixer

 2. Install PySDL via PIP:

   pip2 install PySDL2

 Tested configurations:
 - SDL2 2.0.5 with PySDL2 0.9.3 on Fedora 25 (x86_64)
"""

import os
import sys
from cefpython3 import cefpython as cef
try:
    import sdl2
    import sdl2.ext
except ImportError:
    print "SDL2 module not found - please install"
    sys.exit(1)
try:
    from PIL import Image
except ImportError:
    print "PIL module not found - please install"
    sys.exit(1)

class LoadHandler(object):
    """Simple handler for loading URLs."""
    
    def OnLoadingStateChange(self, browser, is_loading, **_):
        if not is_loading:
            print "loading complete"
            
    def OnLoadError(self, browser, frame, error_code, failed_url, **_):
        if not frame.IsMain():
            return
        print "Failed to load %s" % failed_url
        cef.PostTask(cef.TID_UI, exit_app, browser)

class RenderHandler(object):
    """
    Handler for rendering web pages to the
    screen via SDL2.
    
    The object's texture property is exposed
    to allow the main rendering loop to access
    the SDL2 texture.
    """

    def __init__(self, renderer, width, height):
        self.__width = width
        self.__height = height
        self.__renderer = renderer
        self.texture = None
            
    def GetViewRect(self, rect_out, **_):
        rect_out.extend([0, 0, self.__width, self.__height])
        return True
    
    def OnPaint(self, browser, element_type, paint_buffer, **_):
        """
        Using the pixel data from CEF's offscreen rendering
        the data is converted by PIL into a SDL2 surface
        which can then be rendered as a SDL2 texture.
        """
        if element_type == cef.PET_VIEW:
            image = Image.frombuffer(
                'RGBA',
                (self.__width, self.__height),
                paint_buffer.GetString(mode="rgba", origin="top-left"),
                'raw',
                'BGRA'
            )
            #
            # Following PIL to SDL2 surface code from pysdl2 source.
            #
            mode = image.mode
            rmask = gmask = bmask = amask = 0
            if mode == "RGB":
                # 3x8-bit, 24bpp
                if sdl2.endian.SDL_BYTEORDER == sdl2.endian.SDL_LIL_ENDIAN:
                    rmask = 0x0000FF
                    gmask = 0x00FF00
                    bmask = 0xFF0000
                else:
                    rmask = 0xFF0000
                    gmask = 0x00FF00
                    bmask = 0x0000FF
                depth = 24
                pitch = self.__width * 3
            elif mode in ("RGBA", "RGBX"):
                # RGBX: 4x8-bit, no alpha
                # RGBA: 4x8-bit, alpha
                if sdl2.endian.SDL_BYTEORDER == sdl2.endian.SDL_LIL_ENDIAN:
                    rmask = 0x00000000
                    gmask = 0x0000FF00
                    bmask = 0x00FF0000
                    if mode == "RGBA":
                        amask = 0xFF000000
                else:
                    rmask = 0xFF000000
                    gmask = 0x00FF0000
                    bmask = 0x0000FF00
                    if mode == "RGBA":
                        amask = 0x000000FF
                depth = 32
                pitch = self.__width * 4
            else:
                print "Unsupported mode: %s" % mode
                exit_app()
            
            pxbuf = image.tobytes()
            # create surface
            surface = sdl2.SDL_CreateRGBSurfaceFrom(pxbuf, self.__width, self.__height, depth, pitch, rmask, gmask, bmask, amask)
            if self.texture:
                # free memory used by previous texture
                sdl2.SDL_DestroyTexture(self.texture)
            # create texture
            self.texture = sdl2.SDL_CreateTextureFromSurface(self.__renderer, surface)
            # free the surface
            sdl2.SDL_FreeSurface(surface)
        else:
            print "Unsupport element_type in OnPaint"

def exit_app():
    """Tidy up SDL2 and CEF before exiting."""
    sdl2.SDL_Quit()
    cef.Shutdown()
    print "exited"

def main():
    # the following variables control the dimensions of the window
    # and browser display area
    width = 1024
    height = 768
    headerHeight = 0 # useful if for leaving space for controls at the top of the window (future implementation?)
    browserHeight = height - headerHeight
    browserWidth = width
    # initialise CEF for offscreen rendering
    WindowUtils = cef.WindowUtils()
    sys.excepthook = cef.ExceptHook
    cef.Initialize(settings={"windowless_rendering_enabled": True})
    window_info = cef.WindowInfo()
    window_info.SetAsOffscreen(0)
    # initialise SDL2 for video (add other init constants if you
    # require other SDL2 functionality e.g. mixer,
    # TTF, joystick etc.
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    # create the window
    window = sdl2.video.SDL_CreateWindow(
        'cefpython3 SDL2 Demo',
        sdl2.video.SDL_WINDOWPOS_UNDEFINED,
        sdl2.video.SDL_WINDOWPOS_UNDEFINED,
        width,
        height,
        0
    )
    # define default background colour (black in this case)
    backgroundColour = sdl2.SDL_Color(0, 0, 0)
    # create the renderer using hardware acceleration
    renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
    # set-up the RenderHandler, passing in the SDL2 renderer
    renderHandler = RenderHandler(renderer, width, height - headerHeight)
    # create the browser instance
    browser = cef.CreateBrowserSync(window_info, url="https://www.google.com/")
    browser.SetClientHandler(LoadHandler())
    browser.SetClientHandler(renderHandler)
    # must call WasResized at least once to let know CEF that
    # viewport size is available and that OnPaint may be called.
    browser.SendFocusEvent(True)
    browser.WasResized()
    # begin the main rendering loop
    running = True
    while running:
        # convert SDL2 events into CEF events (where appropriate)
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT or (event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE):
                    running = False
                    break
            if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if event.button.y > headerHeight:
                        # mouse click triggered in browser region
                        browser.SendMouseClickEvent(event.button.x, event.button.y - headerHeight, cef.MOUSEBUTTON_LEFT, False, 1)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if event.button.y > headerHeight:
                        # mouse click triggered in browser region
                        browser.SendMouseClickEvent(event.button.x, event.button.y - headerHeight, cef.MOUSEBUTTON_LEFT, True, 1)
            elif event.type == sdl2.SDL_MOUSEMOTION:
                if event.button.y > headerHeight:
                    # mouse click triggered in browser region
                    browser.SendMouseMoveEvent(event.button.x, event.button.y - headerHeight, True)
        # clear the renderer
        sdl2.SDL_SetRenderDrawColor(renderer, backgroundColour.r, backgroundColour.g, backgroundColour.b, 255)
        sdl2.SDL_RenderClear(renderer)
        # tell CEF to update which will trigger the OnPaint
        # method of the RenderHandler instance
        cef.MessageLoopWork()
        # update display
        sdl2.SDL_RenderCopy(renderer, renderHandler.texture, None, sdl2.SDL_Rect(0, headerHeight, browserWidth, browserHeight))
        sdl2.SDL_RenderPresent(renderer)
    # user exited
    exit_app()
    
if __name__ == "__main__":
    main()
