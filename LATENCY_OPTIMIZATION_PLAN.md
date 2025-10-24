# Latency Optimization Plan

## Current Latency Breakdown

1. **VAD Finalization**: 800ms (waiting for silence to confirm end of speech)
2. **STT Processing**: ~500-1500ms (save WAV file, upload, transcribe)
3. **LLM First Token**: ~300-800ms (request processing + first token)
4. **LLM Full Response**: ~1000-3000ms (streaming full response)
5. **TTS Synthesis**: ~500-2000ms (wait for full text + synthesize entire response)
6. **First Audio Chunk**: ~100-200ms (MP3 decode + PCM conversion)
7. **Post-Response Settling**: ~800ms (echo prevention)

**Total Current Latency: 4-9 seconds** from finish speaking to hearing response

## Optimization Strategy

### Phase 1: Quick Wins (Low Risk, ~40% latency reduction)
**Estimated Time Saved: 1-2 seconds**

#### 1.1 Reduce VAD Finalization Timeout ✅
- **Current**: 800ms silence required
- **Optimized**: 500-600ms
- **Savings**: 200-300ms
- **Risk**: Low - might cut off slow speakers occasionally
- **Config**: `stt_finalize_ms: 500`

#### 1.2 Implement Sentence-Based Streaming TTS 🔥 **BIGGEST WIN**
- **Current**: Wait for entire LLM response, then synthesize once
- **Optimized**: Synthesize and play each complete sentence as LLM streams
- **Savings**: 1000-2000ms (overlap LLM + TTS + playback)
- **Risk**: Medium - might have small gaps between sentences
- **Implementation**: Buffer sentences, synthesize on `.`, `!`, `?`

#### 1.3 Reduce Post-Response Settling
- **Current**: 500ms + 3×150ms = 950ms
- **Optimized**: 300ms + 2×100ms = 500ms
- **Savings**: 450ms
- **Risk**: Low - may need tuning per environment

#### 1.4 Optimize STT File Handling
- **Current**: Write to temp file, then read back
- **Optimized**: Use in-memory BytesIO buffer
- **Savings**: 50-100ms
- **Risk**: Very low

### Phase 2: Medium Optimizations (Medium Risk, ~20% additional reduction)
**Estimated Time Saved: 500-1000ms**

#### 2.1 Parallel LLM + TTS Processing
- **Current**: Sequential buffering
- **Optimized**: TTS synthesis starts as soon as first sentence is complete
- **Savings**: 300-600ms
- **Risk**: Medium - coordination complexity

#### 2.2 Audio Playback Overlap
- **Current**: Wait for sentence fully synthesized before playing
- **Optimized**: Start playback as soon as first audio chunks available
- **Savings**: 100-200ms
- **Risk**: Low

#### 2.3 Reduce TTS Speed Config
- **Current**: `speed: 1.0`
- **Optimized**: `speed: 1.1` (10% faster, still natural)
- **Savings**: 10% of TTS time (~100-200ms)
- **Risk**: Low - slight quality trade-off

### Phase 3: Advanced Optimizations (Higher Risk, ~15% additional reduction)
**Estimated Time Saved: 300-800ms**

#### 3.1 OpenAI Realtime API
- **Current**: Sequential STT → LLM → TTS
- **Optimized**: Single WebSocket connection with streaming I/O
- **Savings**: 500-1000ms (eliminate API round-trips)
- **Risk**: High - complete architecture rewrite
- **Note**: This is the ultimate solution but requires major refactoring

#### 3.2 Predictive TTS Buffering
- **Current**: Wait for sentence end
- **Optimized**: Start synthesis on partial sentences (8-10 words)
- **Savings**: 200-400ms
- **Risk**: High - might cut sentences awkwardly

#### 3.3 Local STT Model (Whisper)
- **Current**: OpenAI API transcription (~500-1500ms)
- **Optimized**: Local Whisper model (~200-500ms on GPU)
- **Savings**: 300-1000ms
- **Risk**: Medium - requires GPU, more complex setup

## Recommended Implementation Order

### Immediate (Today) - Phase 1.1, 1.3
1. ✅ Reduce `stt_finalize_ms` to 500ms
2. ✅ Reduce post-response settling to 500ms
3. ✅ Add latency monitoring/logging

**Expected improvement: 650ms reduction**

### Priority (Next) - Phase 1.2, 1.4
4. 🔥 Implement sentence-based streaming TTS (biggest win!)
5. ✅ Optimize STT to use BytesIO instead of temp files

**Expected improvement: 1000-2000ms additional reduction**

### Optional (If Still Not Satisfied) - Phase 2
6. Parallel LLM + TTS processing
7. Audio playback overlap
8. Increase TTS speed slightly

**Expected improvement: 400-800ms additional reduction**

### Future (Major Refactor) - Phase 3
9. Consider OpenAI Realtime API
10. Local Whisper model

**Expected improvement: 800-2000ms additional reduction**

## Success Metrics

- **Current**: 4-9 seconds average latency
- **After Phase 1**: 2.5-6 seconds (40% reduction)
- **After Phase 2**: 2-5 seconds (60% reduction)
- **After Phase 3**: 1-3 seconds (80% reduction)

## Testing Considerations

- Test with various sentence lengths
- Monitor echo issues after reducing settling times
- Ensure Hebrew text segmentation works correctly
- Validate audio quality with faster speeds

