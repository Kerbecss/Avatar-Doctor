using System;
using System.Collections.Generic;

namespace Teyocesu.AvatarDoctor.Editor.Discovery
{
    internal sealed class AvatarDiscoveryCandidateComparer
        : IComparer<AvatarDiscoveryCandidate>
    {
        internal static readonly AvatarDiscoveryCandidateComparer Instance =
            new AvatarDiscoveryCandidateComparer();

        private AvatarDiscoveryCandidateComparer()
        {
        }

        public int Compare(
            AvatarDiscoveryCandidate left,
            AvatarDiscoveryCandidate right)
        {
            if (ReferenceEquals(left, right))
            {
                return 0;
            }

            if (left == null)
            {
                return -1;
            }

            if (right == null)
            {
                return 1;
            }

            int comparison = CompareScene(left, right);
            if (comparison != 0)
            {
                return comparison;
            }

            comparison = CompareHierarchySiblingIndices(left, right);
            if (comparison != 0)
            {
                return comparison;
            }

            comparison = StringComparer.Ordinal.Compare(
                left.HierarchyDisplayPath,
                right.HierarchyDisplayPath);
            if (comparison != 0)
            {
                return comparison;
            }

            comparison = left.DescriptorComponentOrdinal.CompareTo(
                right.DescriptorComponentOrdinal);
            if (comparison != 0)
            {
                return comparison;
            }

            return left.DescriptorInstanceId.CompareTo(
                right.DescriptorInstanceId);
        }

        private static int CompareScene(
            AvatarDiscoveryCandidate left,
            AvatarDiscoveryCandidate right)
        {
            if (left.IsSavedScene != right.IsSavedScene)
            {
                return left.IsSavedScene ? -1 : 1;
            }

            if (left.IsSavedScene)
            {
                return StringComparer.Ordinal.Compare(
                    left.NormalizedSavedScenePath,
                    right.NormalizedSavedScenePath);
            }

            int comparison = left.LoadedSceneIndex.CompareTo(
                right.LoadedSceneIndex);
            return comparison != 0
                ? comparison
                : StringComparer.Ordinal.Compare(left.SceneName, right.SceneName);
        }

        private static int CompareHierarchySiblingIndices(
            AvatarDiscoveryCandidate left,
            AvatarDiscoveryCandidate right)
        {
            int sharedDepth = Math.Min(left.HierarchyDepth, right.HierarchyDepth);
            for (int depth = 0; depth < sharedDepth; depth++)
            {
                int comparison = left.GetHierarchySiblingIndex(depth).CompareTo(
                    right.GetHierarchySiblingIndex(depth));
                if (comparison != 0)
                {
                    return comparison;
                }
            }

            return left.HierarchyDepth.CompareTo(right.HierarchyDepth);
        }
    }
}
