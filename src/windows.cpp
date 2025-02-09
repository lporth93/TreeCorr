/* Copyright (c) 2003-2019 by Mike Jarvis
 *
 * TreeCorr is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

// This contains hacks to get the installation on Windows working.
// This fixes error LNK2001: unresolved external symbol PyInit__treecorr
// cf. https://techoverflow.net/2022/01/23/how-to-fix-python-cffi-error-lnk2001-unresolved-external-symbol-pyinit__/
void PyInit__treecorr(void) { }
