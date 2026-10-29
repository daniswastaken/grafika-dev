$input v_color0
#include <grafika/config.h>
#if GS_CLOUD_TYPE >= 2
  $input v_color1, v_color2, v_fogColor
#endif

#include <bgfx_shader.sh>
#include <grafika/main.sh>

uniform vec4 CameraPosition;

#define GS_CLOUD_PARAMS(x) GS_CLOUD2##x##STEPS, GS_CLOUD2##x##THICKNESS, GS_CLOUD2##x##RAIN_THICKNESS, GS_CLOUD2##x##VELOCITY, GS_CLOUD2##x##SCALE, GS_CLOUD2##x##DENSITY, GS_CLOUD2##x##SHAPE

void main() {
  vec4 color = v_color0;

  #if GS_CLOUD_TYPE >= 2
    vec3 vDir = normalize(v_color0.xyz);
    vec3 cloudPos = v_color0.xyz;
    cloudPos.xz += CameraPosition.xz;

    #if GS_CLOUD_TYPE == 2
      color = renderCloudsRounded(vDir, cloudPos, v_color1.w, v_color2.w, v_color2.rgb, v_color1.rgb, GS_CLOUD_PARAMS(_));

      #ifdef GS_CLOUD2_LAYER2
        vec2 parallax = vDir.xz / abs(vDir.y) * GS_CLOUD2_LAYER2_OFFSET;
        vec3 offsetPos = cloudPos;
        offsetPos.xz += parallax;
        vec4 color2 = renderCloudsRounded(vDir, offsetPos, v_color1.a, v_color2.a*2.0, v_color2.rgb, v_color1.rgb, GS_CLOUD_PARAMS(_LAYER2_));
        color = mix(color2, color, 0.2 + 0.8*color.a);
      #endif

      #ifdef GS_AURORA
        color += renderAurora(cloudPos, v_color2.a, v_color1.a, v_fogColor)*(1.0-0.95*color.a);
      #endif

      color.a *= v_color0.a;
    #else
      vDir.xz *= 0.3 + v_color0.w; // height parallax

      vec2 p = (vDir.xz)/(0.015 + 0.035*abs(vDir.y));
      p += 0.035*CameraPosition.xz;

      vec4 clouds = renderClouds(p, v_color2.w, v_color1.w, v_color2.rgb, v_color1.rgb, GS_CLOUD3_SCALE, GS_CLOUD3_SPEED, GS_CLOUD3_SHADOW);
      color = clouds;

      #ifdef GS_AURORA
        p.xy *= 34.7;
        color += renderAurora(p.xyy, v_color2.w, v_color1.w, v_fogColor)*(1.0-0.95*color.a);
      #endif

      color.a *= smoothstep(0.0, 0.7, vDir.y);
    #endif

    color.rgb = colorCorrection(color.rgb);
  #endif

  gl_FragColor = color;
}
