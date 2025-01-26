<script lang="ts">
  import { onMount } from 'svelte';
  import Moveable from "svelte-moveable";
  import { tinykeys } from "tinykeys";

  import { calculateCropBox, renderJpegtranCropSpec, type CropBox } from './lib/cropBox';
  import { Client, type ImageInfo, EXAMPLE_IMAGE_ID } from './lib/client';

  type AspectRatio = {
    name: string;
    value: number[];
  };

  // Constants
  const API_CLIENT = new Client();
  const EXAMPLE_IMAGE_URL = API_CLIENT.getImageUrl(EXAMPLE_IMAGE_ID);
  // const EXAMPLE_IMAGE_URL = 'https://placehold.co/640x360';
  const CROPBOX_MOVE_STEP = 0.1;  // Relative to image size (width resp. height)
  const SHELL_SCRIPT_OUTFILE_SUFFIX = '-tran';

  // State
  let currentIndex = 0;
  let imageInfo: ImageInfo | null = null;
  let selectedRatio: AspectRatio;
  let cropBox: CropBox = { left: 0, top: 0, right: 0, bottom: 0 };
  let message = '';
  let messageClass = '';
  let moveableInstance: any = null;
  let imageElement: HTMLImageElement | null = null;
  let cropButton: HTMLButtonElement | null = null;
  let cropBoxElement: HTMLDivElement | null = null;
  let addToScriptButton: HTMLButtonElement | null = null;
  let imageContainerElement: HTMLDivElement | null = null;
  let shellScript = '';
  let addToScriptIsPreferred: boolean = false;
  let addToScriptIsSuggested: boolean = true;  // Until imageInfo is loaded.

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
      imageInfo = await API_CLIENT.iter(index);
      message = '';
      messageClass = '';
    } catch (error) {
      console.error('Failed to load image info:', error);
      message = 'Error loading image';
      messageClass = 'alert';
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
    addToScriptIsPreferred = false;

    try {
      const responseText = await API_CLIENT.tran(imageInfo.current, {
        box: scaledBox,
        aspectRatio: selectedRatio.value
      });
      message = 'Image cropped successfully';
      messageClass = 'success';

      // Reload the image to show changes
      const currentImageUrl = API_CLIENT.getImageUrl(imageInfo.current);
      await fetch(currentImageUrl);
      imageElement.src = `${currentImageUrl}?refresh=${Date.now()}`;
      initializeCropBox();
    } catch (error) {
      console.error('Failed to crop image:', error);
      message = `Failed to crop image: ${error.message}`;
      messageClass = 'alert';
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
    // This function is called on drag, so no need to update moveable.
    // Otherwise, caller should additionally call updateMoveable.
  }

  function moveCropBoxStepwise(stepsX: number, stepsY: number) {
    if (!imageElement) return;
    moveCropBox(
      Math.floor(stepsX * imageElement.width * CROPBOX_MOVE_STEP),
      Math.floor(stepsY * imageElement.height * CROPBOX_MOVE_STEP)
    );
    updateMoveable();
    focusSuggestedButton();
  }

  function addCropCommandToScript() {
    if (!imageInfo?.current || !cropBox) return;
    addToScriptIsPreferred = true;
    const outfileName = imageInfo.current.replace(/(\.[^\.]+)$/, `${SHELL_SCRIPT_OUTFILE_SUFFIX}$1`);
    shellScript += `jpegtran -crop ${renderJpegtranCropSpec(cropBox)} -copy all -outfile ${outfileName} ${imageInfo.current}\n`;
  }

  function focusSuggestedButton() {
    if ((addToScriptIsSuggested || !cropButton) && addToScriptButton) {
      addToScriptButton.focus();
    } else {
      cropButton?.focus();
    }
  }

  onMount(() => {
    tinykeys(window, {
      'Shift+n': () => imageInfo?.prev && loadImageInfo(currentIndex - 1),
      'n': () => imageInfo?.next && loadImageInfo(currentIndex + 1),
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

  $: addToScriptIsSuggested = (
    (imageInfo?.current)? addToScriptIsPreferred : true
  );
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
              src={imageInfo?.current ? API_CLIENT.getImageUrl(imageInfo.current) : EXAMPLE_IMAGE_URL}
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
          <button
            class="button"
            disabled={isExampleImage}
            on:click={addCropCommandToScript}
            bind:this={addToScriptButton}
          >
            {#if isExampleImage}
              Cannot add crop command for example image
            {:else}
              Add crop command to script
            {/if}
          </button>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Left</th>
            <th>Right</th>
            <th>Top</th>
            <th>Bottom</th>
            <th>Jpegtran Crop Spec</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{cropBox.left}</td>
            <td>{cropBox.right}</td>
            <td>{cropBox.top}</td>
            <td>{cropBox.bottom}</td>
            <td><code>{cropBox && renderJpegtranCropSpec(cropBox)}</code></td>
          </tr>
        </tbody>
      </table>
      {#if message}
        <div class="grid-x grid-padding-x align-center">
          <div class="cell medium-6">
            <div class="callout {messageClass}">{message}</div>
          </div>
        </div>
      {/if}
      {#if shellScript}
        <pre class="code-block">{shellScript}</pre>
      {/if}
    </div>
  </div>
</main>
