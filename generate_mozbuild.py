#!/usr/bin/env python

import os
import sys
import posixpath

header = """
# Please note this file is autogenerated from generate_mozbuild.py, so do not modify it directly

"""

footers = {
#
# common -- appears in all of the moz.build files
#
  'base': """
if CONFIG['GNU_CXX']:
    CXXFLAGS += [
        '-Wno-attributes',
        '-Wno-sign-compare',
        '-Wno-unknown-pragmas',
    ]
    if CONFIG['CLANG_CXX']:
        CXXFLAGS += ['-Wno-unused-private-field']

if CONFIG['MOZ_DIRECTX_SDK_PATH'] and not CONFIG['MOZ_HAS_WINSDK_WITH_D3D']:
    CXXFLAGS += ['-I\\'%s/include/\\'' % CONFIG['MOZ_DIRECTX_SDK_PATH']]

DEFINES['NOMINMAX'] = True
DEFINES['_CRT_SECURE_NO_DEPRECATE'] = True
DEFINES['_HAS_EXCEPTIONS'] = 0

if not CONFIG['MOZ_DEBUG']:
    DEFINES['_SECURE_SCL'] = 0

DEFINES['ANGLE_ENABLE_D3D9'] = True
if CONFIG['MOZ_HAS_WINSDK_WITH_D3D']:
    DEFINES['ANGLE_ENABLE_D3D11'] = True

DEFINES['ANGLE_COMPILE_OPTIMIZATION_LEVEL'] = 'D3DCOMPILE_OPTIMIZATION_LEVEL1'
DEFINES['ANGLE_NO_EXCEPTIONS'] = True

# We need these defined to nothing so that we don't get bogus dllimport declspecs
DEFINES['GL_APICALL'] = ""
DEFINES['GL_GLEXT_PROTOTYPES'] = ""
DEFINES['EGLAPI'] = ""
""",
#
# translator -- this is the toplevel gfx/angle moz.build as well
#
  'translator': """
# Only build libEGL/libGLESv2 on Windows
if CONFIG['MOZ_WIDGET_TOOLKIT'] == 'windows':
    DIRS += [ 'src/libGLESv2', 'src/libEGL' ]

EXPORTS.angle += [ 'include/GLSLANG/ShaderLang.h', 'include/GLSLANG/ShaderVars.h' ]
EXPORTS.angle.KHR += [ 'include/KHR/khrplatform.h' ]

LOCAL_INCLUDES += [ 'include', 'src' ]

if CONFIG['GKMEDIAS_SHARED_LIBRARY']:
    NO_VISIBILITY_FLAGS = True

# This tells ANGLE to build the translator with declspec(dllexport) on Windows
# which we need to get these symbols exported from gkmedias
DEFINES['COMPONENT_BUILD'] = True
DEFINES['ANGLE_TRANSLATOR_IMPLEMENTATION'] = True

FINAL_LIBRARY = 'gkmedias'
""",
#
# libGLESv2
#
  'libGLESv2': """

LOCAL_INCLUDES += [ '../../include', '../../src' ]

if CONFIG['MOZ_HAS_WINSDK_WITH_D3D']:
  OS_LIBS += [ 'd3d9', 'dxguid' ]
else:
  EXTRA_DSO_LDOPTS += [
    '\\'%s/lib/%s/d3d9.lib\\'' % (CONFIG['MOZ_DIRECTX_SDK_PATH'], CONFIG['MOZ_D3D_CPU_SUFFIX']),
    '\\'%s/lib/%s/dxguid.lib\\'' % (CONFIG['MOZ_DIRECTX_SDK_PATH'], CONFIG['MOZ_D3D_CPU_SUFFIX']),
  ]

GeckoSharedLibrary('libGLESv2', linkage=None)

RCFILE = SRCDIR + '/libGLESv2.rc'
DEFFILE = SRCDIR + '/libGLESv2.def'

SOURCES['../libANGLE/renderer/d3d/HLSLCompiler.cpp'].flags += ['-DANGLE_PRELOADED_D3DCOMPILER_MODULE_NAMES=\\'{ TEXT("d3dcompiler_47.dll"), TEXT("d3dcompiler_46.dll"), TEXT("d3dcompiler_43.dll") }\\'']

if CONFIG['MOZ_HAS_WINSDK_WITH_D3D']:
    SOURCES['../libANGLE/renderer/d3d/d3d11/SwapChain11.cpp'].flags += ['-DANGLE_RESOURCE_SHARE_TYPE=D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX']

""",
#
# libEGL
#
  'libEGL': """

LOCAL_INCLUDES += [ '../../include', '../../src' ]
USE_LIBS += [ 'libGLESv2' ]

GeckoSharedLibrary('libEGL', linkage=None)

RCFILE = SRCDIR + '/libEGL.rc'
DEFFILE = SRCDIR + '/libEGL.def'
"""
}

import json

platforms = None
relative_dir = None

# these files need to not be part of a unified build because they do not
# play nicely with other files
nonunified_source_files = [
  "HLSLCompiler.cpp",
  # generated parsers
  "glslang_tab.cpp",
  "glslang_lex.cpp",
  "Display.cpp",
  "SwapChain11.cpp"
]

def force_non_unified(s):
  if "SSE2" in s:
    return True
  for pattern in nonunified_source_files:
    if pattern in s:
      return True
  return False

def generate_platform_sources(target=None):
  sources = {}

  targetarg = ""
  if target:
    targetarg = "-R %s " % target

  for plat in platforms:
    gyppath = os.path.join(".", "third_party", "gyp", "gyp")
    res = os.system("%s " % gyppath +
                    "--format=dump_mozbuild " +
                    "--ignore-environment " +
                    "--depth=. " +
                    "-Ibuild/standalone.gypi " + 
                    "-Ibuild/common.gypi " +
                    "-DOS=%s " % plat +
                    "-DMSVS_VERSION=2012 " +
                    "-Dangle_standalone=1 " +
                    "-Dangle_build_samples=0 " +
                    "-Dangle_build_tests=0 " +
                    "-Drelease_symbols=true " +
                    targetarg +
                    "build/ANGLE.gyp")
    if res != 0:
      print 'Failed to generate sources for ' + plat
      continue

    f = open('sources.json');
    s = set(map(lambda x: "src/" + x, json.load(f)))
    sources[plat] = s
    f.close()

  return dict(sources.items())


def generate_separated_sources(platform_sources):
  blacklist = [
  ]

  def isblacklisted(value):
    for item in blacklist:
      if value.find(item) >= 0:
        return True

    return False

  separated = {
    'common': set(),
    'android': set(),
    'linux': set(),
  }

  for plat in platform_sources.keys():
    if not separated.has_key(plat):
      separated[plat] = set()

    for value in platform_sources[plat]:
      if isblacklisted(value):
        continue

      found = True
      for other in platforms:
        if other == plat or not platform_sources.has_key(other):
          continue

        if not value in platform_sources[other]:
          found = False
          break

      if found:
        separated['common'].add(value)
      else:
        separated[plat].add(value)

  return separated

def uniq(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

def write_cflags(f, values, subsearch, cflag, indent, prefix):
  def write_indent(indent):
    for _ in range(indent):
        f.write(' ')

  # make all dirs relative to global relative_dir
  val_list = uniq(sorted(map(lambda val: posixpath.relpath(val, relative_dir), values), key=lambda x: x.lower()))

  if len(val_list) == 0:
    return

  if prefix:
    f.write(prefix)

  for val in val_list:
    if val.find(subsearch) > 0:
      write_indent(indent)
      f.write("SOURCES[\'" + val + "\'].flags += [\'" + cflag + "\']\n")


def write_list(f, name, values, indent, prefix=None):
  def write_indent(indent):
    for _ in range(indent):
        f.write(' ')

  # make all dirs relative to global relative_dir
  val_list = uniq(sorted(map(lambda val: posixpath.relpath(val, relative_dir), values), key=lambda x: x.lower()))

  if len(val_list) == 0:
    return

  if prefix:
    f.write(prefix)

  write_indent(indent)
  f.write(name + ' += [\n')
  for val in val_list:
    write_indent(indent + 4)
    f.write('\'' + val + '\',\n')

  write_indent(indent)
  f.write(']\n')

  if name == 'SOURCES':
    for val in val_list:
      if 'SSE2' in val:
        write_indent(indent)
        f.write("SOURCES['%s'].flags += CONFIG['SSE2_FLAGS']\n" % val)

def write_mozbuild(includes, sources, target):
  if target is "translator":
    filename = "moz.build"
  elif target is "libGLESv2":
    filename = "src/libGLESv2/moz.build"
  elif target is "libEGL":
    filename = "src/libEGL/moz.build"
  else:
    print "Don't know how to create moz.build for target %s" % (target)
    sys.exit(1)

  ensured_targets = ['common', 'android', 'mac', 'linux', 'win']
  for src_target in ensured_targets:
    if src_target not in sources:
      sources[src_target] = set()

  f = open(filename, 'wb')

  f.write(header)

  write_list(f, 'EXPORTS.angle', includes, 0)

  def write_sources(slist, prefix=None):
    nonunified = filter(force_non_unified, slist)
    unified = list(set(slist).difference(set(nonunified)))

    if unified:
      write_list(f, 'UNIFIED_SOURCES', unified, 4 if prefix else 0, prefix)
    if nonunified:
      write_list(f, 'SOURCES', nonunified, 4 if prefix else 0, prefix)

  common_d3d11 = filter(lambda s: "/d3d11/" in s, sources['common'])
  common_without_d3d11 = filter(lambda s: "/d3d11/" not in s, sources['common'])

  write_sources(common_without_d3d11)

  write_sources(common_d3d11,
                "if CONFIG['MOZ_HAS_WINSDK_WITH_D3D']:\n")

  write_sources(sources['android'],
                "if CONFIG['MOZ_WIDGET_TOOLKIT'] in ('android', 'gonk'):\n")

  write_sources(sources['mac'],
                "if CONFIG['MOZ_WIDGET_TOOLKIT'] == 'cocoa':\n")

  write_sources(sources['linux'],
                "if CONFIG['MOZ_WIDGET_GTK']:\n")

  write_sources(sources['linux'],
                "if CONFIG['MOZ_WIDGET_TOOLKIT'] == 'qt':\n")

  write_sources(sources['win'],
                "if CONFIG['MOZ_WIDGET_TOOLKIT'] == 'windows':\n")

  f.write("\n")
  f.write(footers['base'])
  f.write("\n")

  if target in footers:
    f.write(footers[target])

  f.close()

  print 'Wrote ' + filename

def main():
  targets = [None]
  global platforms, relative_dir

  target_platforms = {
    "translator": ['win', 'linux', 'mac', 'android'],
    "libGLESv2": ['win'],
    "libEGL": ['win']
  }

  target_dirs = {
    "translator": ".",
    "libGLESv2": "src/libGLESv2",
    "libEGL": "src/libEGL"
  }

  for target in target_platforms.keys():
    platforms = target_platforms[target]
    relative_dir = target_dirs[target]

    includes = dict()
    platform_sources = generate_platform_sources(target)
    separated_sources = generate_separated_sources(platform_sources)
    write_mozbuild(includes, separated_sources, target)

if __name__ == '__main__':
  main()
