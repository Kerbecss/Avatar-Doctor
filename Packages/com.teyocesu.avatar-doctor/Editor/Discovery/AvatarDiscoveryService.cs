using System.Collections.Generic;
using Teyocesu.AvatarDoctor.Editor.Integrations.VRChat;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

namespace Teyocesu.AvatarDoctor.Editor.Discovery
{
    internal sealed class AvatarDiscoveryService
    {
        internal AvatarDiscoveryResult Discover()
        {
            List<AvatarDiscoveryCandidate> candidates =
                new List<AvatarDiscoveryCandidate>();

            for (int sceneIndex = 0;
                sceneIndex < SceneManager.sceneCount;
                sceneIndex++)
            {
                Scene scene = SceneManager.GetSceneAt(sceneIndex);
                if (!IsSceneEligible(scene))
                {
                    continue;
                }

                VRChatAvatarDescriptorBoundary.AppendCandidates(
                    scene,
                    sceneIndex,
                    candidates);
            }

            for (int index = candidates.Count - 1; index >= 0; index--)
            {
                if (!VRChatAvatarDescriptorBoundary.IsCandidateLive(
                    candidates[index]))
                {
                    candidates.RemoveAt(index);
                }
            }

            candidates.Sort(AvatarDiscoveryCandidateComparer.Instance);
            return new AvatarDiscoveryResult(candidates);
        }

        internal static bool IsSceneEligible(Scene scene)
        {
            return scene.IsValid()
                && scene.isLoaded
                && !EditorSceneManager.IsPreviewScene(scene);
        }

        internal static bool IsCandidateLive(
            AvatarDiscoveryCandidate candidate)
        {
            return VRChatAvatarDescriptorBoundary.IsCandidateLive(candidate);
        }
    }
}
