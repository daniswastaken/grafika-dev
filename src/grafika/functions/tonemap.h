#ifndef TONEMAP_H
#define TONEMAP_H

#include "utils.h"

vec3 colorCorrection(vec3 col) {
  #ifdef GS_EXPOSURE
    col *= GS_EXPOSURE;
  #endif

  // ref - https://64.github.io/tonemapping/
  #if GS_TONEMAP_TYPE == 3
    // extended reinhard tonemap
    const float whiteScale = 0.063;
    col = col*(1.0+col*whiteScale)/(1.0+col);
  #elif GS_TONEMAP_TYPE == 4
    // aces tonemap
    const float a = 1.04;
    const float b = 0.03;
    const float c = 0.93;
    const float d = 0.56;
    const float e = 0.14;
    col *= 0.85;
    col = clamp((col*(a*col + b)) / (col*(c*col + d) + e), 0.0, 1.0);
  #elif GS_TONEMAP_TYPE == 2
    // simple reinhard tonemap
    col = col/(1.0+col);
  #elif GS_TONEMAP_TYPE == 1
    // exponential tonemap
    col = 1.0-exp(-col*0.8);
  #endif

  // gamma correction
  col = pow(col, vec3_splat(1.0/GS_GAMMA));

  #ifdef GS_SATURATION
    col = mix(vec3_splat(luminance(col)), col, GS_SATURATION);
  #endif

  #ifdef GS_TINT
    col *= mix(GS_TINT_LOW, GS_TINT_HIGH, col);
  #endif

  return col;
}

// inv used in fogcolor for nether
vec3 colorCorrectionInv(vec3 col) {
  #ifdef GS_TINT
    col /= mix(GS_TINT_LOW, GS_TINT_HIGH, col); // not accurate inverse
  #endif

  #ifdef GS_SATURATION
    col = mix(vec3_splat(dot(col,vec3(0.21, 0.71, 0.08))), col, 1.0/GS_SATURATION);
  #endif

  // incomplete
  // extended reinhard only
  float ws = 0.7966;
  col = pow(col, vec3_splat(GS_GAMMA));
  col = col*(ws + col)/(ws + col*(1.0 - ws));

  #ifdef GS_EXPOSURE
    col /= GS_EXPOSURE;
  #endif

  return col;
}

#endif
