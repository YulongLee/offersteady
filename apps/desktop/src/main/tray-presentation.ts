import { nativeImage, type Menu, type NativeImage, type Tray } from "electron";

// PNG renditions of the existing mint tile/glyph design. NativeImage cannot
// decode the former SVG data URL on Electron 42; never restore an empty icon.
const NORMAL_IMAGES = {"稳": {"16": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACA0lEQVR4AZSQTUhUURTH//e+SYcc06QMjcmhDBGKSKMC+wT7oOxjYZvBohYRrYKgpFVCEG1skctatBCbNlNMySiIrv1AQWT8AEdBBMev0VFHR5x3PeeK47wRlLmcc9655/1///fulaBVM+4rezrW7Hs23mxSqn3SZC0zhEJyI2D0CIEHAAT2X0KQVhDDrBTKqCOKAmktAgSzktyqkkkVjyMyNolQ54AeB/92YHkipPvUwizfAZltvVKmCe+Nl/BXv8OIpwWDP33o/vQdre4P+F3uxtr84pZwpwo2SGyVqXC9oRa2g3YU3a1Af4MHJTX3cfLxTWQXFWB1JpzQbjdyu+HnemQFfV8bsRFdw8gvP8pqnyO2sASeZ+ZmY9TbzjJLWgzseYfgqrqqBYVXzkPabIiFIzrXl1b0PLVYDPjLQ3RuFk20dSLUNYDwYFBndGqOx7vSYhBbXIbz1mV9BxX1b5FVeBR5Z4qRc8qJix9fgY+R6mAxyCo4grOvn2jNdHcA0alZTPcE4Ky8hCCdP/Djz66LlFqdVAx7JhzH85FfXorSF49QXF2J4SY/hM3A7abPyMhxJKkBNlCWCW3ueL7A4TyG3NMncO6NG/e89bj27T0Ol7hgZBwgRSKUVAr/E9s0G2alEvE6+gWK9GgCFLOy0fWwVyF+QSn8IwuaU907FGuZYXYTAAD//0vXZ/8AAAAGSURBVAMACCXPGWVZpMsAAAAASUVORK5CYII=", "32": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAEZklEQVR4AbxWD0yUZRj/fR8UiP8QDJYoYApOESztRmA4SgebVDrWgjkislJcWjlztVgtoRarFnP252KWZJRKTmEI4QnusgFp0TBS6rgOLrippaiEiAR8vc8D3wns+L4bed7ued/ned7n/f1+3/vnu5Mx5pPRdiQ+s7XCmGmvbMlsq1BuiRGWwCTsMXQYJYCIZUi1kLARijJ/bPGEY8ISmIRNHCNxZDUQA0eZWE14qhdCmGsYnwWIhFGQJw3nPN9JSGJOwSTzvghVwr+9X8FJ3LKsSJm3l/kmG3HLkKWVN1MT8BRlApOGpwhu2Z3TPnCjD5ebW2ErNaMhfw9++/LIMALwy0clOLBsHX5+t8iZc9sRt4MP4XgT+nt6cTT9VRyMz4IpIwc/5hXC+s0xnCk8BBLV3XEBzXvKeHpr+QlUpm5z2hWLnfN6jaYAbz9f9F66MgojNDkOhpxn0dvZhfrXPnSOkdh/7OegmuLm1mgKIPREYw5SSgvgFxxAIaI3PYGAqHkwb3wLnWf+gH9EKNZWG5HW8DUi0oZuctjqBzFjQTjX6zWaAugpr1o70HnWhsF/+xnL8V0DLPu+RbfjL44nBQXg9K79qHtlJ1oOmDjX33Mdp3ILcc3xN8dajaaA7vbzYpl3sZEYAmosKGYiw+sbKMS52ka0lpnRXn2SY2oc5gbOXb94mUJN0xQwaeYMLMx6DOEpCU6QuY+uwKL1axCSuAwJO7e7tGn3hDjr9RxZq2ByyF2I2ZKOqeGzoH58A6cj+vk09HVdw/cvvufSumwOtVy3l/UqlIEBtIg9V+uai8px9rNS+PhPwZKX1rk09cCqc7R6WWuQxiz7qvjKka9a08clQkQZOmpOubSeC51qqW6vKYDudGPBV3wF1ae6X7wDfAOmiWsWhktNVpemskqyJjyXaVacP9nERVHPpcLL14f9YEMUVhXlCVGBWH34A9y7NQOLsx/HfduexMwlkUg178bKz9/EgowUTA4J4jlajaaAOaseEEQBCBtxCwhM8pJwfEMeTmzOh7XEhF+NB2GvqsPF0xZY9lfhT1M9fi+ugO1QDZVrmqYAWurET3Lgdecdo0DsVfUcjxQWuyObc7bDxzF93hz2m78ox0DvDfbHazQF0KSpYXdTN8rUJ5v9sAGStxeP9V3tFluTi8CYSPz09m7O0e9DW2Ut++M1ugJcTYzenMb7Tb8DQeJMUE3NMztQnfUG2o/9QCESCl5GRHoygmMXczxe47YA/8gwBEbPh7efD0KT4vigEeii9Wux8Ok1mP2QgY3emnHvbMGsFUuxdPtTmKJzEN0WEJ//Ai+xb6A/8TqNrmeMWJHl728FWWzuJhboLNBxZEiSVafGc8OCW8agon9XPCVBcMuDkrLXU/h6uMQtF4c/UgcFn+oV3/JxwUncMgHvnZuSLUQM/Z2hhKdNgYk5BQ8LED1EIlmI8PxKiCdnLiIV5hQgfBKRPQhlOQsRJ5Ry/9d4PmEJYsIW5EPvbB4A/gMAAP//mDNE+gAAAAZJREFUAwAnP+ZczkkX8QAAAABJRU5ErkJggg=="}, "O": {"16": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABjklEQVR4AZSRzyuDcRzH399nwkaTtJabIzlg2UoO/AHMgZNwExexclCSOXHAAQcHtUJ2cNFmOTiagxoiLUlZoWyKy5pYz74+n8dW47usfft+fjzvz+f17ul5NNAZigUcww+hwEgslKGQRSLDu8wQCo0bAVNECPQCECh+hKBdQQyzmpAmL1F0UdIhQDCrkVtPSWTeMrP8DcgsT8228bMbXK35cb3uRyISzapKEWygqHd7RwhPrwJSQmYkTjzLuN8/VvZYUAwyX2lcruygY3ECLZODRrjmx3C+5IPUdWZ+hWKQir8ZC7a2RqNysjmauODj9d2o+UkxKK+pNubJxxejcsr15dafGWu5UA2sVbA7mxHdOkDyOYHkUxy320HUd7aizFKJv0cx4AXXwjjSyRRC7imE+jzQP9Nwzo3ySImCBhZ7Hbo3Z9Ef9mHg1IeujRmYbbUKzAIbSG4KRZm5AqbKikKjnCY1+tWHuadSK7OaFLqXXoFuaTgBklltt8F9IaG3S4kgWZBO+f8reZcZZr8BAAD//xyUJVwAAAAGSURBVAMA5lSeGaVq/LIAAAAASUVORK5CYII=", "32": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAADN0lEQVR4AbxWW0hUURRd92pWvgqt1Cyzl0Yhah8VhX0kGWpRUvbRjPMhgvYRYY8vIcTqJ+mvD52iSPuoLCHQxAkVgiITikxTsnxQmjKl4rNQ53b20Tljw6jn2jjD7H32XvfstdbM3HsYFU4vY2fFflNHZZGp63mbqbNSc0sQF+Mkbic5/GOAhFUor6AgG5q2zXnzonviYpzETRqzeVR7wy5Uc2E7sFQrM8K1Zvi5AQYUMfGkGWzpFwVJXJMpqfx3Ya5Y7dk30yRtVdUUk2eVHWqkrUJVEh2Qhyumrbr1btfrnz0d/CbUO0f7bROTGOroxlBnD7SpKYIWFboNWN+3wmLIQ9k+E6pOXUbVyUt4vCcDNZn5GGjp0G1Cl4GWe89Qm1WAgdZpoRVBgaAg1Z8fPsNizEPbw2pqpUPaQO+bRjTeesSJow0pSKsz4/iLIh5ptWZEnUnm194V3geZ4Y1EkjKg2TQ0FJg5XWRqAuIuGOET6M97Sj6r/BF/MQPrD+6mFg3XbvNVJkkZGLcOYKyvn/NFGaY/KW+cUrQxhSND7d2YGB7j9UJJysDo9z7BExARJmrnImBjqIBGuh0zAnRRSBn4MzgsRr1XLhe1c+ET6Ceg2TMCdFFIGfANDRaj8xGPWwfFPt8Qx4wAXRRSBvw3hIjRX01fRO1c9H9qF5Bf+DpRz1dIGaC7PDhm+v9Js7nc5clHp2FT8ROuFbo3Bl4+y3i9UJIyQCRxuUZa0N/8FS/P3cBoj5X3lEa+9aEu+zqGu35Qi9hcA19lkrSBNbFRiDmbzjl76z+i4th5PE3I5FF5Ihd0RNNFOg9Wb4+gUiqkDRDbzqw0HLpzBUG7tlKLybHfPKghg4dLrooTkTCZ0GWACNfG7wAJpdeXIrmsECnlN3H6bSkS7+YLY7RPNnQbsBOr3l4I3BKOgE1hULy87LDuddEGdCvNMaBCUeZ+sOcYchvMtFXYtBq3EeolYtqqTdFK9M65az9pqw8ij76GhmJ3kUrzME3SVmmgZHNqDjNhodojocHCNZkYN8BWMOAIM7H03wT75FyLRFkIA6wmEzk2aAe4EXaHEva/weeJiwkTNxPP4dhM+gsAAP//gM/nVAAAAAZJREFUAwCu1jlc/ovcvwAAAABJRU5ErkJggg=="}} as const;

export function companionTrayImages(global: boolean) {
  const png = NORMAL_IMAGES[global ? "O" : "稳"];
  const normal = nativeImage.createFromBuffer(Buffer.from(png[16], "base64"));
  normal.addRepresentation({ scaleFactor: 2, buffer: Buffer.from(png[32], "base64") });
  const transparent = nativeImage.createFromBitmap(Buffer.alloc(16 * 16 * 4), { width: 16, height: 16 });
  const retina = nativeImage.createFromBitmap(Buffer.alloc(32 * 32 * 4), { width: 32, height: 32 });
  transparent.addRepresentation({ scaleFactor: 2, buffer: retina.toPNG() });
  return { normal, transparent };
}

interface TrayPresentationOptions {
  readonly platform: string;
  readonly images: { normal: NativeImage; transparent: NativeImage };
  readonly isHidden: () => boolean;
  readonly restore: () => void;
  readonly showMenu: (menu: Menu) => void;
}

/** Keep the same native status item and event target throughout hide/restore. */
export class CompanionTrayPresentation {
  private menu: Menu | null = null;
  constructor(private readonly tray: Tray, private readonly options: TrayPresentationOptions) {
    tray.on("click", () => { if (options.isHidden()) options.restore(); });
    if (options.platform === "win32") {
      tray.on("double-click", () => { if (options.isHidden()) options.restore(); });
    }
    // macOS otherwise opens an attached context menu on left mouse-down. Keep
    // left-click as direct restore while hidden and expose the menu on right-click.
    if (options.platform === "darwin") {
      tray.on("right-click", () => {
        if (options.isHidden() && this.menu) options.showMenu(this.menu);
      });
    }
  }
  update(menu: Menu) { this.menu = menu; this.refresh(); }
  refresh() {
    const hidden = this.options.isHidden();
    this.tray.setImage(hidden ? this.options.images.transparent : this.options.images.normal);
    this.tray.setContextMenu(hidden && this.options.platform === "darwin" ? null : this.menu);
  }
}
