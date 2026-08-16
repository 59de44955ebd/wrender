# wrender

wrender (short for "WebView2-render") is a simple commandline tool for Windows 11 that allows to render/convert files/URLs using a headless [Microsoft Edge WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2). WebView2 is based on recent Chromium versions and preinstalled in Windows 11.

The main purpose of wrender is to render SVGs as (raster-graphics) images, but it can also be used render other inputs, see below.

Since it relies on creating a new browser process, wrender is not particularly fast, but this applies to any headless browser. wrender uses a user profile in %LOCALAPPDATA%\WebView2 which it creates when run for the first time resp. if the profile doesn't exist yet. It always runs in private mode, so without leaving history entries in this profile.

## Usage

```cmd
$ wrender -h
Usage:

 wrender <input> <output> [options...]
 wrender -h              Show this help
 wrender -u              Check for online update

Options:

 --page-margins=n,n,n,n  Top,bottom,left,right page margin in mm.
                         Default: 10,10,10,10
                         Applicable: input=<url>|.htm|.html|.md, output=.pdf|PRINTER

 --page-size=n,n         Page width and height in mm.
                         Default: 210,297 (=Din A4)
                         Applicable: input=<url>|.htm|.html|.md, output=.pdf|PRINTER

 --view-width=n          View width in pixel.
                         Default: 1024
                         Applicable: input=<url>|.htm|.html|.md, output=.jpg|.jpeg|.png

 --wait=n                After DOM content is loaded wait n milliseconds before rendering.
                         Default: 0
                         Applicable: input=<url>|.htm|.html

Input:                   Supported Outputs:

 <url>                   .jpeg .jpg .png .pdf PRINTER
 .avif                   .jpeg .jpg .png .pdf .webp PRINTER
 .bmp                    .jpeg .jpg .png .pdf .webp PRINTER
 .gif                    .jpeg .jpg .png .pdf .webp PRINTER
 .htm                    .jpeg .jpg .png .pdf PRINTER
 .html                   .jpeg .jpg .png .pdf PRINTER
 .ico                    .jpeg .jpg .png .pdf .webp PRINTER
 .jpeg                   .jpeg .jpg .png .pdf .webp PRINTER
 .jpg                    .jpeg .jpg .png .pdf .webp PRINTER
 .json                   .xml
 .md                     .html .jpeg .jpg .png .pdf PRINTER
 .png                    .jpeg .jpg .png .pdf .webp PRINTER
 .svg                    .jpeg .jpg .png .pdf .webp PRINTER
 .webp                   .jpeg .jpg .png .pdf .webp PRINTER
 .xml                    .json

If PRINTER is specified as output, wrender tries to print with the default printer.
```

### Examples

* Render .svg as .png  
  `$ wrender input.svg output.png`

* Render .html as .png (with default width 1024 px)   
  `$ wrender input.html output.png`

* Render URL as .pdf (landscape page orientation)  
  `$ wrender https://google.com/ google.pdf --page-size=210,297`

* Render .md (markdown) as .html  
  `$ wrender input.md output.html`

* Render .md (markdown) as .png with width 800 px  
  `$ wrender input.md output.html --view-width=800`
