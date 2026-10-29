#ifndef SKY_H
#define SKY_H

#include "detection.h"
#include "noise.h"

struct gs_skycolor {
  vec3 zenith;
  vec3 horizon;
  vec3 horizonEdge;
};

// rainbow spectrum
vec3 spectrum(float x) {
  vec3 s = vec3(x-0.5, x, x+0.5);
  s = smoothstep(1.0,0.0,abs(s));
  return s*s;
}

vec3 getUnderwaterCol(vec3 FOG_COLOR) {
  return 2.0*GS_UNDERWATER_TINT*FOG_COLOR*FOG_COLOR;
}

vec3 getEndZenithCol() {
  return GS_END_ZENITH_COL;
}

vec3 getEndHorizonCol() {
  return GS_END_HORIZON_COL;
}

gs_skycolor gsEndSkyColors(gs_environment env) {
  gs_skycolor s;
  s.zenith = getEndZenithCol();
  s.horizon = getEndHorizonCol();
  s.horizonEdge = s.horizon;
  return s;
}

gs_skycolor gsOverworldSkyColors(gs_environment env) {
  gs_skycolor s;
  float f = 1.0 + 2.0*(1.0-max(-env.dayFactor, 0.0));
  float nightFactor = step(env.dayFactor, 0.0);
  s.zenith = mix(GS_DAY_ZENITH_COL, GS_NIGHT_ZENITH_COL*f, nightFactor);
  s.horizon = mix(GS_DAY_HORIZON_COL, GS_NIGHT_HORIZON_COL*f, nightFactor);
  s.horizonEdge = mix(GS_DAY_EDGE_COL, GS_NIGHT_EDGE_COL*f, nightFactor);

  float dawnFactor = 1.0-env.dayFactor*env.dayFactor;
  dawnFactor *= dawnFactor*dawnFactor;
  dawnFactor *= mix(1.0, dawnFactor*dawnFactor, nightFactor);
  s.zenith = mix(s.zenith, GS_DAWN_ZENITH_COL, dawnFactor);
  s.horizon = mix(s.horizon, GS_DAWN_HORIZON_COL, dawnFactor);
  s.horizonEdge = mix(s.horizonEdge, GS_DAWN_EDGE_COL, dawnFactor);

  float zh = dot(s.zenith, vec3_splat(0.33));
  float hh = dot(s.horizon, vec3_splat(0.33));
  float rainMix = env.rainFactor*GS_SKY_RAIN_MIX_FACTOR;
  s.zenith = mix(s.zenith, GS_RAIN_ZENITH_COL*zh, rainMix);
  s.horizon = mix(s.horizon, GS_RAIN_HORIZON_COL*hh, rainMix);
  s.horizonEdge = mix(s.horizonEdge, s.horizon, env.rainFactor);

  if (env.underwater) {
    vec3 underwaterFog = env.fogCol*env.fogCol*GS_UNDERWATER_TINT;
    s.zenith = mix(2.0*underwaterFog, underwaterFog*zh, 0.8);
    s.horizon = mix(2.0*underwaterFog, underwaterFog*hh, 0.8);
    s.horizonEdge = s.horizon;
  }

  return s;
}

gs_skycolor gsSkyColors(gs_environment env) {
  if (env.end) {
    return gsEndSkyColors(env);
  }
  return gsOverworldSkyColors(env);
}


vec3 renderOverworldSky(gs_skycolor skyCol, gs_environment env, vec3 viewDir, bool isSkyPlane) {
  float avy = abs(viewDir.y);
  float mask = 0.5 + (0.5*viewDir.y/(0.4 + avy));

  vec2 g = clamp(0.5 - 0.5*vec2(dot(env.sunDir, viewDir), dot(env.moonDir, viewDir)), 0.0, 1.0);
  // rain == 1 skips sqrt: mix(sqrt(g), g, 1.0) == g (exact)
  vec2 g1 = (env.rainFactor >= 1.0) ? 1.0-g : 1.0-mix(sqrt(g), g, env.rainFactor);
  vec2 g2 = g1*g1;
  vec2 g4 = g2*g2;
  vec2 g8 = g4*g4;
  float mg8 = (g8.x+g8.y)*mask*(1.0-0.9*env.rainFactor);

  float vh = 1.0 - viewDir.y*viewDir.y;
  float vh2 = vh*vh;
  vh2 = mix(vh2, mix(1.0, vh2*vh2, GS_SKY_VOID_FACTOR), step(viewDir.y, 0.0));
  vh2 = mix(vh2, 1.0, mg8);
  float vh4 = vh2*vh2;

  float gradient1 = vh4*vh4;
  float gradient2 = 0.8*gradient1 + 0.2*vh2;
  gradient1 *= gradient1;
  gradient1 = mix(gradient1*gradient1, 1.0, mg8);
  gradient2 = mix(gradient2, 1.0, mg8);

  float dawnFactor = 1.0-env.dayFactor*env.dayFactor;
  float df = mix(1.0, g2.x, dawnFactor*dawnFactor);
  float df2 = df*df;
  vec3 sky = mix(skyCol.horizon, skyCol.horizonEdge, gradient1*df2);
  sky = mix(skyCol.zenith, sky, gradient2*df);

  sky *= 0.5+0.5*gradient2;
  sky *= (1.0 + (2.0*mg8 + 7.0*mg8*mg8)*mask)*mix(1.0, mask, GS_SKY_VOID_DARKNESS);

  #ifdef GS_FOG_GLARE
  if (!isSkyPlane) {
    float source = max(0.0, (mg8-0.22)/0.78);
    source *= source;
    source *= source;
    sky *= 1.0 + 15.0*source*(1.0-env.rainFactor);
  }
  #endif

  #ifdef GS_RAINBOW
    float rainbowFade = 0.5 + 0.5*viewDir.y;
    rainbowFade *= rainbowFade;
    rainbowFade *= mix(GS_RAINBOW_CLEAR, GS_RAINBOW_RAIN, env.rainFactor);
    rainbowFade *= 0.5+0.5*env.dayFactor;
    if (rainbowFade > 0.0) {
      sky += spectrum(24.2*(0.85-g.x))*rainbowFade*skyCol.horizon;
    }
  #endif

  return sky;
}

vec3 renderEndSky(vec3 horizonCol, vec3 zenithCol, vec3 viewDir, float t) {
  t *= 0.1; // Animation time scale

  // --- Center of the Black Hole ---
  vec3 bhPos = normalize(vec3(0.6, 0.35, -0.65)); 
  vec3 forward = bhPos;
  vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
  vec3 up = cross(forward, right);
  
  vec2 uv = vec2(dot(viewDir, right), dot(viewDir, up));
  float d = length(uv); 
  float faceMask = step(0.0, dot(viewDir, forward));

  #ifdef GS_CINEMATIC_SKY
    /* 
       CINEMATIC SKY: High-resolution volumetric black-hole rendering.
       Features: Gravitational Lensing, Accretion Disk, Event Horizon, Back-Arcs.
       Performance: Very intensive. Only recommended for high-end GPUs.
    */
    float rs = 0.18; 
    vec3 diff = bhPos - viewDir;
    float lens = (rs * rs * 1.5) / (d*d + 0.0001);
    lens = min(lens, 1.5); 
    vec3 lensedDir = normalize(viewDir + diff * lens * smoothstep(rs, rs*4.0, d));

    // --- Procedural End Sky (Background) ---
    float a = atan2(lensedDir.x, lensedDir.z);
    float n1 = 0.5 + 0.5*sin(3.0*a + t + 10.0*lensedDir.x*lensedDir.y);
    float n2 = 0.5 + 0.5*sin(5.0*a + 0.5*t + 5.0*n1 + 0.1*sin(40.0*a -4.0*t));
    float waves = 0.7*n2*n1 + 0.3*n1;
    float grad = 0.5 + 0.5*lensedDir.y;
    float streaks = waves*(1.0 - grad*grad*grad);
    streaks += (1.0-streaks)*smoothstep(1.0-waves, -1.0, lensedDir.y);
    float f = 0.3*streaks + 0.7*smoothstep(1.0, -0.5, lensedDir.y);
    float h = streaks*streaks;
    float g = h*h;
    g *= g;

    vec3 sky = mix(zenithCol, horizonCol, f*f);
    sky += (0.1*streaks + 2.0*g*g*g + h*h*h)*vec3(2.0,0.5,0.0);
    sky += 0.25*streaks*spectrum(sin(2.0*lensedDir.x*lensedDir.y+t));

    // --- Accretion Disk & Glow ---
    vec3 diskColorHot   = vec3(1.0, 0.95, 0.70);
    vec3 diskColorMid   = vec3(1.0, 0.45, 0.05);
    vec3 diskColorCool  = vec3(0.55, 0.08, 0.01);

    float tilt = 6.5; 
    vec2 diskUv  = vec2(uv.x, uv.y * tilt);
    float diskD  = length(diskUv); 
    float diskInner = rs * 1.1; 
    float diskOuter = rs * 3.5; 

    float diskT = clamp((diskD - diskInner) / (diskOuter - diskInner), 0.0, 1.0);
    float diskAlpha = smoothstep(diskOuter * 1.1, diskOuter * 0.85, diskD)
                    * smoothstep(diskInner * 0.85, diskInner * 1.0,  diskD);
    float diskHeat = pow(1.0 - diskT, 1.2) * 0.85 + 0.15;

    float angle = atan2(diskUv.y, diskUv.x);
    float diskN1 = noise3D(vec3(diskUv * 18.0, t * 2.5 - angle * 1.8));
    float diskN2 = noise3D(vec3(diskUv * 40.0, t * 4.0 + angle * 0.8));
    float diskNoise = diskN1 * 0.65 + diskN2 * 0.35;

    vec3 diskColor = mix(diskColorHot, diskColorMid, smoothstep(0.0, 0.85, diskT));
    diskColor      = mix(diskColor, diskColorCool,   smoothstep(0.35, 1.0, diskT));

    float innerBloom = 0.08 / (abs(diskD - diskInner) + 0.05);
    innerBloom *= smoothstep(diskOuter, diskInner, diskD); 
    float noiseVar = 0.55 + 0.45 * diskNoise;
    
    vec3 finalDisk = (diskHeat * diskAlpha * noiseVar * diskColor + innerBloom * diskColorHot) * 3.5;

    // Lensed Back-Arcs
    float arcDist = abs(d - rs * 1.1);
    float arcVertMask = smoothstep(rs * 0.02, rs * 0.1, abs(uv.y)); 
    float arcRadialMask = smoothstep(rs * 2.8, rs * 0.9, d);        
    float arcNoise = noise3D(vec3(uv * 22.0, t * 2.0 + angle * 1.5));
    float arcGlow = (0.022 / (arcDist + 0.004)) * arcVertMask * arcRadialMask * (0.65 + 0.35 * arcNoise);
    vec3 arcColor = mix(diskColorHot, diskColorMid, clamp(d / (rs * 2.5), 0.0, 1.0));
    sky += arcGlow * arcColor * 5.5 * faceMask;
    sky += finalDisk * faceMask; 

    // Singularity & Photon Rings
    float inBH = (1.0 - smoothstep(rs * 0.92, rs * 1.0, d)) * faceMask;
    sky *= (1.0 - inBH); 

    float pCore = (0.005 / (abs(d - rs * 1.01) + 0.0003));
    float pBloom = (0.012 / (abs(d - rs * 1.01) + 0.012));
    float pBloomMask = smoothstep(rs * 3.5, rs * 1.2, d) * faceMask;
    sky += (pCore * 8.0 + pBloom * 1.2) * mix(diskColorHot, vec3(1.0, 1.0, 1.0), 0.8) * pBloomMask;

    float distortedD = length(uv * vec2(1.0, 1.05)); 
    float iDist = abs(distortedD - rs * 0.78);
    float iVar = 0.85 + 0.15 * sin(atan2(uv.y, uv.x) * 2.5 + t);
    float iVertFade = smoothstep(0.0, rs * 0.3, abs(uv.y));
    float iCore = (0.0015 / (iDist + 0.00015)) * smoothstep(rs * 0.015, 0.0, iDist);
    float iDiff = (0.008 / (iDist + 0.02)) * smoothstep(rs * 0.08, rs * 0.01, iDist);
    sky += (iCore * 10.0 + iDiff * 2.5) * iVertFade * iVar * inBH * mix(diskColorHot, vec3(1.0, 1.0, 1.0), 0.7);

    float frontMask = smoothstep(rs * 0.06, -rs * 0.02, uv.y);
    sky += finalDisk * frontMask * inBH;

  #else
    // --- Simplified High-Performance End Sky ---
    float a = atan2(viewDir.x, viewDir.z);
    float waves = 0.5 + 0.5*sin(3.0*a + t + 10.0*viewDir.x*viewDir.y);
    float f = smoothstep(1.0, -0.5, viewDir.y);
    vec3 sky = mix(zenithCol, horizonCol, f*f);
    sky += 0.2 * waves * vec3(1.0, 0.4, 0.0);
  #endif

  return sky;
}

vec3 gsRenderSky(gs_skycolor skycol, gs_environment env, vec3 viewDir, float t, bool isSkyPlane) {
  vec3 sky;
  viewDir.y = -viewDir.y;

  if (env.end) {
    // Optimization: We only render the heavy cinematic black hole 
    // when we are reasonably sure it should be visible (e.g. background sky).
    // isSkyPlane being false or viewDir pointing too far down should skip it.
    if (isSkyPlane && viewDir.y > -0.2) {
      sky = renderEndSky(skycol.horizon, skycol.zenith, viewDir, t);
    } else {
      sky = skycol.horizon; 
    }
  } else {
    // isSkyPlane = true here skips the glare math in renderOverworldSky
    sky = renderOverworldSky(skycol, env, viewDir, isSkyPlane);
  }

  return sky;
}

// shooting star
vec3 gsRenderShootingStar(vec3 viewDir, vec3 FOG_COLOR, float t) {
  // exact early-out: final term scales by dayFade, 0 glow nothing to add
  float dayFade = max(1.0-FOG_COLOR.r-FOG_COLOR.g-FOG_COLOR.b, 0.0);
  if (dayFade == 0.0) {
    return vec3_splat(0.0);
  }

  // transition vars
  float h = t / (GS_SHOOTING_STAR_DELAY + GS_SHOOTING_STAR_PERIOD);
  float h0 = floor(h);
  t = (GS_SHOOTING_STAR_DELAY + GS_SHOOTING_STAR_PERIOD) * (h-h0);
  t = min(t/GS_SHOOTING_STAR_PERIOD, 1.0);
  float t0 = t*t;
  float t1 = 1.0-t0;
  t1 *= t1; t1 *= t1; t1 *= t1;

  // randomize size, rotation, add motion, add skew
  float r = fract(sin(h0) * 43758.545313);
  float a = 6.2831*r;
  float cosa = cos(a);
  float sina = sin(a);
  vec2 uv = viewDir.xz * (6.0 + 4.0*r);
  uv = vec2(cosa*uv.x + sina*uv.y, -sina*uv.x + cosa*uv.y);
  uv.x += t1 - t;
  uv.x -= 2.0*r + 3.5;
  uv.y += viewDir.y * 3.0;

  // draw star
  float g = 1.0-min(abs((uv.x-0.95))*20.0, 1.0); // source glow
  float s = 1.0-min(abs(8.0*uv.y), 1.0); // line
  s *= s*s*smoothstep(-1.0+1.96*t1, 0.98-t, uv.x); // decay tail
  s *= s*s*smoothstep(1.0, 0.98-t0, uv.x); // decay source
  s *= 1.0-t1; // fade in
  s *= 1.0-t0; // fade out
  s *= 0.7 + 16.0*g*g;
  s *= dayFade; // fade out during day
  return s*vec3(0.8, 0.9, 1.0);
}

// Galaxy stars - needs further optimization
vec3 gsRenderGalaxy(vec3 vdir, vec3 fogColor, gs_environment env, float t) {
  // exact early-out: result scales by visibility, 0 glow nothing to add
  float visibility = mix(1.0, GS_GALAXY_DAY_VISIBILITY, env.dayFactor)*(1.0-env.rainFactor);
  if (env.underwater || visibility == 0.0) {
    return vec3_splat(0.0);
  }

  t *= GS_GALAXY_SPEED;

  // rotate space
  float cosb = sin(0.2*t);
  float sinb = cos(0.2*t);
  vdir.xy = mul(mtxFromRows(vec2(cosb, sinb), vec2(-sinb, cosb)), vdir.xy);

  // noise
  float n0 = 0.5 + 0.5*sin(5.0*vdir.x)*sin(5.0*vdir.y - 0.5*t)*sin(5.0*vdir.z + 0.5*t);
  float n1 = noise3D(15.0*vdir + sin(0.85*t + 1.3));
  float n2 = noise3D(50.0*vdir + 1.0*n1 + sin(0.7*t + 1.0));
  float n3 = noise3D(200.0*vdir - 10.0*sin(0.4*t + 0.500));

  // stars
  n3 = smoothstep(0.04,0.3,n3+0.02*n2);
  float gd = vdir.x + 0.1*vdir.y + 0.1*sin(10.0*vdir.z + 0.2*t);
  float st = n1*n2*n3*n3*(1.0+70.0*gd*gd);
  st = (1.0-st)/(1.0+400.0*st);
  vec3 stars = (0.8 + 0.2*sin(vec3(8.0,6.0,10.0)*(2.0*n1+0.8*n2) + vec3(0.0,0.4,0.82)))*st;

  // glow
  float gfmask = abs(vdir.x)-0.15*n1+0.04*n2+0.25*n0;
  float gf = 1.0 - (vdir.x*vdir.x + 0.03*n1 + 0.2*n0);
  gf *= gf;
  gf *= gf*gf;
  gf *= 1.0-0.3*smoothstep(0.2, 0.3, gfmask);
  gf *= 1.0-0.2*smoothstep(0.3, 0.4, gfmask);
  gf *= 1.0-0.1*smoothstep(0.2, 0.1, gfmask);
  vec3 gfcol = normalize(vec3(n0, cos(2.0*vdir.y), sin(vdir.x+n0)));
  stars += (0.4*gf + 0.012)*mix(vec3(0.5, 0.5, 0.5), gfcol*gfcol, GS_GALAXY_VIBRANCE);

  return stars*visibility;
}


#endif
