using System;
using System.Collections.Generic;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using UnityEngine;
using UnityObject = UnityEngine.Object;

namespace Teyocesu.AvatarDoctor.Editor.Selection
{
    internal sealed class AvatarSelectionModel
    {
        private readonly Func<AvatarDiscoveryCandidate, bool> isCandidateLive;

        internal AvatarSelectionModel()
            : this(AvatarDiscoveryService.IsCandidateLive)
        {
        }

        internal AvatarSelectionModel(
            Func<AvatarDiscoveryCandidate, bool> isCandidateLive)
        {
            this.isCandidateLive = isCandidateLive
                ?? throw new ArgumentNullException(nameof(isCandidateLive));
            DiscoveryResult = new AvatarDiscoveryResult(
                Array.Empty<AvatarDiscoveryCandidate>());
            CurrentSelection = AvatarSelection.CreateEmpty();
        }

        internal AvatarDiscoveryResult DiscoveryResult { get; private set; }

        internal AvatarSelection CurrentSelection { get; private set; }

        internal AvatarSelection ApplyDiscoveryResult(
            AvatarDiscoveryResult discoveryResult,
            UnityObject activeEditorSelection)
        {
            if (discoveryResult == null)
            {
                throw new ArgumentNullException(nameof(discoveryResult));
            }

            AvatarDiscoveryResult liveResult = CreateLiveResult(discoveryResult);
            AvatarSelection nextSelection = ResolveAfterRefresh(
                liveResult.Candidates,
                activeEditorSelection,
                CurrentSelection);

            DiscoveryResult = liveResult;
            CurrentSelection = nextSelection;
            return CurrentSelection;
        }

        internal AvatarSelection ApplyEditorSelection(
            UnityObject activeEditorSelection)
        {
            AvatarDiscoveryResult liveResult = CreateLiveResult(DiscoveryResult);
            AvatarSelection nextSelection = ResolveEditorSelection(
                liveResult.Candidates,
                activeEditorSelection,
                CurrentSelection);

            DiscoveryResult = liveResult;
            CurrentSelection = nextSelection;
            return CurrentSelection;
        }

        internal bool TrySelectManual(AvatarDiscoveryCandidate candidate)
        {
            AvatarDiscoveryResult liveResult = CreateLiveResult(DiscoveryResult);
            AvatarDiscoveryCandidate reboundCandidate = candidate == null
                ? null
                : FindUniqueCandidateByIdentity(
                    liveResult.Candidates,
                    candidate.DescriptorIdentity);

            AvatarSelection nextSelection;
            if (reboundCandidate == null)
            {
                nextSelection = ResolveAfterRefresh(
                    liveResult.Candidates,
                    null,
                    CurrentSelection);
            }
            else if (liveResult.Candidates.Count == 1)
            {
                nextSelection = AvatarSelection.CreateSelected(
                    reboundCandidate,
                    AvatarSelectionOrigin.AutomaticSingle);
            }
            else
            {
                nextSelection = AvatarSelection.CreateSelected(
                    reboundCandidate,
                    AvatarSelectionOrigin.Manual);
            }

            DiscoveryResult = liveResult;
            CurrentSelection = nextSelection;
            return reboundCandidate != null;
        }

        private AvatarDiscoveryResult CreateLiveResult(
            AvatarDiscoveryResult discoveryResult)
        {
            List<AvatarDiscoveryCandidate> liveCandidates =
                new List<AvatarDiscoveryCandidate>();
            foreach (AvatarDiscoveryCandidate candidate in discoveryResult.Candidates)
            {
                if (isCandidateLive(candidate))
                {
                    liveCandidates.Add(candidate);
                }
            }

            return new AvatarDiscoveryResult(liveCandidates);
        }

        private static AvatarSelection ResolveAfterRefresh(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates,
            UnityObject activeEditorSelection,
            AvatarSelection currentSelection)
        {
            AvatarSelection countSelection = ResolveCountState(candidates);
            if (countSelection != null)
            {
                return countSelection;
            }

            AvatarDiscoveryCandidate reboundCandidate = RebindCurrentSelection(
                candidates,
                currentSelection);
            if (reboundCandidate != null
                && currentSelection.Origin == AvatarSelectionOrigin.Manual)
            {
                return AvatarSelection.CreateSelected(
                    reboundCandidate,
                    AvatarSelectionOrigin.Manual);
            }

            if (reboundCandidate != null
                && IsAutomaticOrigin(currentSelection.Origin))
            {
                return AvatarSelection.CreateSelected(
                    reboundCandidate,
                    currentSelection.Origin.Value);
            }

            AvatarDiscoveryCandidate mappedCandidate = MapEditorSelection(
                candidates,
                activeEditorSelection);
            return mappedCandidate != null
                ? AvatarSelection.CreateSelected(
                    mappedCandidate,
                    AvatarSelectionOrigin.AutomaticEditorSelection)
                : AvatarSelection.CreateUnresolved();
        }

        private static AvatarSelection ResolveEditorSelection(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates,
            UnityObject activeEditorSelection,
            AvatarSelection currentSelection)
        {
            AvatarSelection countSelection = ResolveCountState(candidates);
            if (countSelection != null)
            {
                return countSelection;
            }

            AvatarDiscoveryCandidate reboundCandidate = RebindCurrentSelection(
                candidates,
                currentSelection);
            if (reboundCandidate != null
                && currentSelection.Origin == AvatarSelectionOrigin.Manual)
            {
                return AvatarSelection.CreateSelected(
                    reboundCandidate,
                    AvatarSelectionOrigin.Manual);
            }

            AvatarDiscoveryCandidate mappedCandidate = MapEditorSelection(
                candidates,
                activeEditorSelection);
            if (mappedCandidate != null)
            {
                return AvatarSelection.CreateSelected(
                    mappedCandidate,
                    AvatarSelectionOrigin.AutomaticEditorSelection);
            }

            return reboundCandidate != null
                && IsAutomaticOrigin(currentSelection.Origin)
                    ? AvatarSelection.CreateSelected(
                        reboundCandidate,
                        currentSelection.Origin.Value)
                    : AvatarSelection.CreateUnresolved();
        }

        private static AvatarSelection ResolveCountState(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates)
        {
            if (candidates.Count == 0)
            {
                return AvatarSelection.CreateEmpty();
            }

            return candidates.Count == 1
                ? AvatarSelection.CreateSelected(
                    candidates[0],
                    AvatarSelectionOrigin.AutomaticSingle)
                : null;
        }

        private static AvatarDiscoveryCandidate RebindCurrentSelection(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates,
            AvatarSelection currentSelection)
        {
            return currentSelection.State == AvatarSelectionState.Selected
                ? FindUniqueCandidateByIdentity(
                    candidates,
                    currentSelection.Candidate.DescriptorIdentity)
                : null;
        }

        private static AvatarDiscoveryCandidate FindUniqueCandidateByIdentity(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates,
            UnityObject descriptorIdentity)
        {
            if (descriptorIdentity == null)
            {
                return null;
            }

            AvatarDiscoveryCandidate match = null;
            foreach (AvatarDiscoveryCandidate candidate in candidates)
            {
                if (candidate.DescriptorIdentity == null
                    || candidate.DescriptorIdentity != descriptorIdentity)
                {
                    continue;
                }

                if (match != null)
                {
                    return null;
                }

                match = candidate;
            }

            return match;
        }

        private static AvatarDiscoveryCandidate MapEditorSelection(
            IReadOnlyList<AvatarDiscoveryCandidate> candidates,
            UnityObject activeEditorSelection)
        {
            GameObject selectedGameObject = activeEditorSelection as GameObject;
            if (selectedGameObject == null)
            {
                Component selectedComponent = activeEditorSelection as Component;
                if (selectedComponent != null)
                {
                    selectedGameObject = selectedComponent.gameObject;
                }
            }

            if (selectedGameObject == null)
            {
                return null;
            }

            Transform ancestor = selectedGameObject.transform;
            while (ancestor != null)
            {
                AvatarDiscoveryCandidate match = null;
                foreach (AvatarDiscoveryCandidate candidate in candidates)
                {
                    if (candidate.AvatarRoot != ancestor.gameObject)
                    {
                        continue;
                    }

                    if (match != null)
                    {
                        return null;
                    }

                    match = candidate;
                }

                if (match != null)
                {
                    return match;
                }

                ancestor = ancestor.parent;
            }

            return null;
        }

        private static bool IsAutomaticOrigin(
            AvatarSelectionOrigin? origin)
        {
            return origin == AvatarSelectionOrigin.AutomaticSingle
                || origin == AvatarSelectionOrigin.AutomaticEditorSelection;
        }
    }
}
