export type ImageInfo = {
  current: string;
  prev: string | null;
  next: string | null;
  total: number;
};

export const EXAMPLE_IMAGE_ID = 'example';

export class Client {
  private apiUrlBase: string;

  constructor(apiUrlBase: string = '') {
    // Note that specifying a different API URL would require the
    // server to add the Access-Control-Allow-Origin header.
    // A proxy server is configured in vite.config.ts so this
    // shouldn’t be necessary.
    this.apiUrlBase = apiUrlBase;
  }

  getImageUrl(imageId: string): string {
    return `${this.apiUrlBase}/image/${imageId}`;
  }

  async iter(index: number): Promise<ImageInfo> {
    const response = await fetch(`${this.apiUrlBase}/iter/${index}`);
    if (response.ok) {
      const imageInfo = await response.json();
      if (!['current', 'prev', 'next', 'total'].every(key => Object.hasOwn(imageInfo, key))) {
        throw new Error('Invalid image info' + JSON.stringify(imageInfo));
      }
      return imageInfo;
    } else {
      throw new Error(response.statusText);
    }
  }

  async tran(imageId: string, data: any): Promise<string> {
    const response = await fetch(`${this.apiUrlBase}/tran/${imageId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (response.ok) {
      return await response.text();
    } else {
      throw new Error(response.statusText);
    }
  }
}