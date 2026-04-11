/**
 * KIRA — Image Uploader Component
 *
 * Multi-image upload (3-5 images) with preview and type selection.
 * Each image can be tagged as: interior, exterior, shelf_closeup.
 *
 * Owner: Frontend Lead
 * Phase: 5.2
 *
 * Props:
 *   images (array) — Current uploaded images [{file, preview, type}]
 *   onImagesChange (function) — Callback when images change
 */

import { useState } from 'react';

export default function ImageUploader({ images = [], onImagesChange }) {
  // TODO: Implement multi-image upload with:
  //   - Drag-and-drop zone
  //   - File input (accept="image/jpeg,image/png")
  //   - Image preview thumbnails
  //   - Image type selector per image (interior/exterior/shelf_closeup)
  //   - Remove image button
  //   - 3-5 image count validation
  //   - 2MB per image size validation
  //   - Visual feedback for valid/invalid state

  return (
    <div>
      {/* TODO: Implement image upload UI */}
      <p>Image Uploader — Upload 3-5 store images</p>
    </div>
  );
}
