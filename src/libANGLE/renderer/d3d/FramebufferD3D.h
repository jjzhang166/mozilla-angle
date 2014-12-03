//
// Copyright 2014 The ANGLE Project Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//

// FramebufferD3D.h: Defines the DefaultAttachmentD3D and FramebufferD3D classes.

#ifndef LIBANGLE_RENDERER_D3D_FRAMBUFFERD3D_H_
#define LIBANGLE_RENDERER_D3D_FRAMBUFFERD3D_H_

#include "libANGLE/renderer/FramebufferImpl.h"

namespace rx
{
class RenderTarget;
class RendererD3D;

class DefaultAttachmentD3D : public DefaultAttachmentImpl
{
  public:
    DefaultAttachmentD3D(RenderTarget *renderTarget);
    virtual ~DefaultAttachmentD3D();

    static DefaultAttachmentD3D *makeDefaultAttachmentD3D(DefaultAttachmentImpl* impl);

    virtual GLsizei getWidth() const override;
    virtual GLsizei getHeight() const override;
    virtual GLenum getInternalFormat() const override;
    virtual GLenum getActualFormat() const override;
    virtual GLsizei getSamples() const override;

    RenderTarget *getRenderTarget() const;

  private:
    RenderTarget *mRenderTarget;
};

class FramebufferD3D : public FramebufferImpl
{
  public:
    FramebufferD3D(RendererD3D *renderer);
    virtual ~FramebufferD3D();

  private:
    RendererD3D *const mRenderer;
};

}

#endif // LIBANGLE_RENDERER_D3D_FRAMBUFFERD3D_H_