<script lang="ts">
  import { onMount } from 'svelte';
  import Moveable from "svelte-moveable";
  import { calculateCropBox, type CropBox } from './lib/cropBox';
  import { tinykeys } from "tinykeys";

  // Types
  type ImageInfo = {
    current: string;
    prev: string | null;
    next: string | null;
    total: number;
  };

  type AspectRatio = {
    name: string;
    value: number[];
  };

  // Constants
  const EXAMPLE_IMAGE = '/image/example';
  // const EXAMPLE_IMAGE = 'https://placehold.co/640x360';
  const CROPBOX_MOVE_STEP = 0.1;  // Relative to image size (width resp. height)

  // State
  let currentIndex = 0;
  let imageInfo: ImageInfo | null = null;
  let selectedRatio: AspectRatio;
  let cropBox: CropBox = { left: 0, top: 0, right: 0, bottom: 0 };
  let message = '';
  let moveableInstance: any = null;
  let imageElement: HTMLImageElement | null = null;
  let cropButton: HTMLButtonElement | null = null;
  let cropBoxElement: HTMLDivElement | null = null;
  let imageContainerElement: HTMLDivElement | null = null;

  const aspectRatios: AspectRatio[] = [
    { name: '16:9', value: [16, 9] },
    { name: '4:3', value: [4, 3] },
    { name: '1:1', value: [1, 1] },
    { name: '3:4', value: [3, 4] },
    { name: '9:16', value: [9, 16] }
  ];

  selectedRatio = aspectRatios[0];

  // Functions
  async function loadImageInfo(index: number) {
    currentIndex = index;
    try {
      const response = await fetch(`/iter/${index}`);
      const data = await response.json();
      if (!response.ok) {
        message = data.description || 'Failed to load image';
        imageInfo = null;
      } else {
        imageInfo = {
          current: data.current,
          prev: data.prev,
          next: data.next,
          total: data.total
        };
        message = '';
      }
    } catch (error) {
      console.error('Failed to load image info:', error);
      message = 'Error loading image';
      imageInfo = null;
    }
    
    // Reset crop box when image changes, regardless of success/failure
    if (imageElement) {
      initializeCropBox();
    }
  }

  function initializeCropBox() {
    if (!imageElement) return;
    
    cropBox = calculateCropBox(
      { width: imageElement.width, height: imageElement.height },
      selectedRatio.value[0] / selectedRatio.value[1]
    );

    updateMoveable();
  }

  function updateMoveable() {
    if (!moveableInstance) return;

    moveableInstance.updateRect();
  }

  function getOriginalScaleCropBox() {
    if (!imageElement) return;

    // Calculate crop box coordinates relative to original image size
    const scale = Math.min(
      imageElement.naturalWidth / imageElement.width,
      imageElement.naturalHeight / imageElement.height,
    );
    return {
      left: Math.round(cropBox.left * scale),
      top: Math.round(cropBox.top * scale),
      right: Math.round(cropBox.right * scale),
      bottom: Math.round(cropBox.bottom * scale)
    };
  }

  async function cropImage() {
    const scaledBox = getOriginalScaleCropBox();
    if (!scaledBox || !imageElement || !imageInfo?.current ) return;

    try {
      const response = await fetch(`/tran/${imageInfo.current}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          box: scaledBox,
          aspectRatio: selectedRatio.value
        })
      });

      if (response.ok) {
        message = 'Image cropped successfully';
        // Reload the image to show changes
        await fetch(`/image/${imageInfo.current}`);
        imageElement.src = `/image/${imageInfo.current}?refresh=${Date.now()}`;
        initializeCropBox();
      } else {
        // const error = await response.json();
        const responseText = await response.text();
        message = `Failed to crop: ${responseText || 'Unknown error'}`;
      }
    } catch (error) {
      console.error('Failed to crop image:', error);
      message = 'Failed to crop image';
    }
  }

  function showCropBoxMessage() {
    const cropBox = getOriginalScaleCropBox();
    if (cropBox) {
      message = `${JSON.stringify(cropBox)}`;
    }
  }

  function moveCropBox(deltaX: number, deltaY: number) {
    if (!imageElement) return;

    // Calculate new position while maintaining size
    const cropBoxWidth = cropBox.right - cropBox.left;
    const cropBoxHeight = cropBox.bottom - cropBox.top;
    let newLeft = cropBox.left + deltaX;
    let newTop = cropBox.top + deltaY;

    // Constrain to image bounds
    newLeft = Math.max(0, Math.min(newLeft, imageElement.width - cropBoxWidth));
    newTop = Math.max(0, Math.min(newTop, imageElement.height - cropBoxHeight));

    // Update crop box while maintaining size
    cropBox = {
      left: newLeft,
      top: newTop,
      right: newLeft + cropBoxWidth,
      bottom: newTop + cropBoxHeight
    };
    showCropBoxMessage();
    // This function is called on drag, so no need to update moveable.
    // Otherwise, caller should additionally call updateMoveable.
  }

  function moveCropBoxStepwise(stepsX: number, stepsY: number) {
    if (!imageElement) return;
    moveCropBox(
      stepsX * imageElement.width * CROPBOX_MOVE_STEP,
      stepsY * imageElement.height * CROPBOX_MOVE_STEP
    );
    updateMoveable();
    cropButton?.focus();
  }

  onMount(() => {
    tinykeys(window, {
      'Shift+n': () => loadImageInfo(currentIndex - 1),
      'n': () => loadImageInfo(currentIndex + 1),
      'ArrowUp': () => moveCropBoxStepwise(0, -1),
      'ArrowDown': () => moveCropBoxStepwise(0, 1),
      'ArrowLeft': () => moveCropBoxStepwise(-1, 0),
      'ArrowRight': () => moveCropBoxStepwise(1, 0),
    });
    loadImageInfo(currentIndex);
  });

  $: if (selectedRatio) {
    initializeCropBox();
  }

  $: isExampleImage = !imageInfo?.current;
</script>

<main class="grid-container fluid">
  <div class="grid-x grid-padding-x">
    <div class="cell">
      <div class="grid-x grid-padding-x">
        <div class="cell small-4 text-left">
          <button 
            class="button small"
            disabled={!imageInfo?.prev} 
            on:click={() => loadImageInfo(currentIndex - 1)}
          >
            Previous {imageInfo?.prev !== null ? `(${currentIndex - 1})` : ''}
          </button>
        </div>
        <div class="cell small-4 text-center">
          {#if imageInfo?.current}
            {imageInfo.current} ({currentIndex + 1}/{imageInfo.total})
          {:else}
            No images
          {/if}
        </div>
        <div class="cell small-4 text-right">
          <button 
            class="button small"
            disabled={!imageInfo?.next} 
            on:click={() => loadImageInfo(currentIndex + 1)}
          >
            Next {imageInfo?.next !== null ? `(${currentIndex + 1})` : ''}
          </button>
        </div>
      </div>

      <div class="grid-x grid-padding-x margin-vertical-1">
        {#each aspectRatios as ratio}
          <div class="cell shrink">
            <label class="margin-0">
              <input
                type="radio"
                name="aspect-ratio"
                value={ratio}
                bind:group={selectedRatio}
              >
              {ratio.name}
            </label>
          </div>
        {/each}
      </div>

      <div class="grid-x grid-padding-x align-center">
        <div class="cell text-center">
          <div class="image-container" bind:this={imageContainerElement}>
            <img
              bind:this={imageElement}
              src={imageInfo?.current ? `/image/${imageInfo.current}` : EXAMPLE_IMAGE}
              alt="Current image"
              on:load={initializeCropBox}
            >
            {#if imageElement}
              <Moveable
                bind:this={moveableInstance}
                target={cropBoxElement}
                draggable={true}
                origin={false}
                onDrag={({ delta: [dx, dy] }) => moveCropBox(dx, dy)}
              />
              <div 
                class="crop-box"
                bind:this={cropBoxElement}
                style="
                  left: {cropBox.left}px;
                  top: {cropBox.top}px;
                  width: {cropBox.right - cropBox.left}px;
                  height: {cropBox.bottom - cropBox.top}px;
                "
              ></div>
            {/if}
            {#if isExampleImage}
              <div class="image-credit">
                Image credit: <a href="https://www.pexels.com/photo/ukrainian-flags-beside-rotes-rathaus-in-berlin-11739000/" target="_blank" rel="noopener noreferrer">Pexels</a>
              </div>
            {/if}
          </div>
        </div>
      </div>

      <div class="grid-x grid-padding-x align-center">
        <div class="cell shrink">
          <button 
            class="button"
            disabled={!imageInfo} 
            on:click={cropImage}
            bind:this={cropButton}
            on:keydown={(event) => { if (event.key === 'Enter') { cropImage(); } }}
          >
            {#if isExampleImage}
              Cannot crop example image
            {:else}
              Crop
            {/if}
          </button>
        </div>
      </div>
      {#if message}
        <div class="grid-x grid-padding-x align-center">
          <div class="cell medium-6">
            <div class="callout">{message}</div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</main>
