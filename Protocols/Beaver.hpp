/*
 * Beaver.cpp
 *
 */

#ifndef PROTOCOLS_BEAVER_HPP_
#define PROTOCOLS_BEAVER_HPP_

#include "Beaver.h"

#include "Replicated.hpp"
#include "./Tools/SimpleIndex.h"
#include <array>
#include "cryptoTools/Common/CuckooIndex.h"
#include "OT/OTExtension.h"
#include "OT/OTExtensionWithMatrix.h"
#include "Tools/time-func.h"
#include <vector>
#include <algorithm>

#define RECEIVER_INPUT PREP_DIR "OT-receiver%d-input"
#define RECEIVER_OUTPUT PREP_DIR "OT-receiver%d-output"
#define SENDER_OUTPUT PREP_DIR "OT-sender%d-output%d"

template <class T>
typename T::Protocol Beaver<T>::branch()
{
    typename T::Protocol res(P);
    res.prep = prep;
    res.MC = MC;
    res.init_mul();
    return res;
}

template <class T>
void Beaver<T>::init(Preprocessing<T> &prep, typename T::MAC_Check &MC)
{
    this->prep = &prep;
    this->MC = &MC;
}

template <class T>
void Beaver<T>::init_mul()
{
    assert(this->prep);
    assert(this->MC);
    shares.clear();
    opened.clear();
    triples.clear();
    lengths.clear();
}

template <class T>
void Beaver<T>::prepare_mul(const T &x, const T &y, int n)
{
    (void)n;
    triples.push_back({{}});
    auto &triple = triples.back();
    triple = prep->get_triple(n);
    shares.push_back(x - triple[0]);
    shares.push_back(y - triple[1]);
    lengths.push_back(n);
}

template <class T>
void Beaver<T>::exchange()
{
    assert(shares.size() == 2 * lengths.size());
    MC->init_open(P, shares.size());
    for (size_t i = 0; i < shares.size(); i++)
        MC->prepare_open(shares[i], lengths[i / 2]);
    MC->exchange(P);
    for (size_t i = 0; i < shares.size(); i++)
        opened.push_back(MC->finalize_raw());
    it = opened.begin();
    triple = triples.begin();
}

template <class T>
void Beaver<T>::start_exchange()
{
    MC->POpen_Begin(opened, shares, P);
}

template <class T>
void Beaver<T>::stop_exchange()
{
    MC->POpen_End(opened, shares, P);
    it = opened.begin();
    triple = triples.begin();
}

template <class T>
T Beaver<T>::finalize_mul(int n)
{
    (void)n;
    typename T::open_type masked[2];
    T &tmp = (*triple)[2];
    for (int k = 0; k < 2; k++)
    {
        masked[k] = *it++;
    }
    tmp += (masked[0] * (*triple)[1]);
    tmp += ((*triple)[0] * masked[1]);
    tmp += T::constant(masked[0] * masked[1], P.my_num(), MC->get_alphai());
    triple++;
    return tmp;
}

template <class T>
void Beaver<T>::check()
{
    assert(MC);
    MC->Check(P);
}

template <class T>
void Beaver<T>::cisc(SubProcessor<T> &proc, const Instruction &instruction)
{
    octetStream cs;
    int r0 = instruction.get_r(0);
    // , lambda = T::clear::MAX_N_BITS;
    // std::cout << "Bit length is " << lambda << std::endl;
    bigint signal = 0;
    string tag((char *)&r0, 4);
    // std::cout << "tag: "<< tag << std::endl;

    if (tag == string("PSI_", 4))
    {
        // std::cout << P.my_num() << std::endl;
        // std::cout <<  instruction.get_r(1) <<" "<<  instruction.get_r(2)<< " "<<  instruction.get_r(3)<< std::endl;

        typedef uint64_t idtype;

        // typename T::clear result;
        auto &args = instruction.get_start();
        fstream r;
        int m = args.back();
        std::cout << "m: " << m << std::endl;
        r.open("Player-Data/psi/P" + to_string(P.my_num()), ios::in);
        std::vector<osuCrypto::block> ids;
        std::vector<idtype> smallids;
        idtype r_tmp;
        for (size_t i = 0; i < m; i++)
        {
            r >> r_tmp;
            smallids.push_back(r_tmp);
            ids.push_back(osuCrypto::block(r_tmp));
        }
        r.close();
        // for (size_t i = 0; i < m; i++)
        // {
        //     std::cout << ids[i] << " ";
        // }
        // std::cout << std::endl;

        // ssp 40
        int ssp = 40;
        osuCrypto::CuckooParam params = oc::CuckooIndex<>::selectParams(m, ssp, 0, 3);
        int nbase = 128;
        size_t l = sizeof(idtype) * 8;
        int nOTs = l * params.numBins();
        PRNG G;
        G.ReSeed();
        OT_ROLE ot_role;
        // std::cout << params.numBins() << std::endl;
        osuCrypto::CuckooIndex<> cuckoo;
        SimpleIndex sIdx;
        if (P.my_num() == RECEIVER_P)
        {
            osuCrypto::block cuckooSeed;
            cuckoo.init(params);
            cuckoo.insert(ids, cuckooSeed);
            cuckoo.print();
            ot_role = RECEIVER;
        }
        else
        {
            osuCrypto::block cuckooSeed;
            sIdx.init(params.numBins(), m, ssp, 3);
            sIdx.insertItems(ids, cuckooSeed);
            sIdx.print();
            ot_role = SENDER;
        }

        cout << "begin base ot \n";
        // base ot
        timeval baseOTstart, baseOTend;
        gettimeofday(&baseOTstart, NULL);
        RealTwoPartyPlayer *rP = new RealTwoPartyPlayer(P.N, 1 - P.my_num(), "machine");
        BaseOT bot = BaseOT(nbase, 128, rP, INV_ROLE(ot_role));
        bot.exec_base();
        gettimeofday(&baseOTend, NULL);
        double basetime = timeval_diff(&baseOTstart, &baseOTend);
        cout << "BaseTime (" << role_to_str(ot_role) << "): " << basetime / 1000000 << endl
             << flush;
        // Receiver send something to force synchronization
        // (since Sender finishes baseOTs before Receiver)
        octetStream os;
        if (P.my_num() == RECEIVER_P)
        {
            bigint a = 3;
            a.pack(cs);
            P.send_to(1, cs);
        }
        else
        {
            P.receive_player(RECEIVER_P, cs);
            bigint a;
            a.unpack(cs);
            // cout << a << endl;
        }

        // convert baseOT selection bits to BitVector
        // (not already BitVector due to legacy PVW code)
        BitVector baseReceiverInput = bot.receiver_inputs;
        baseReceiverInput.resize(nbase);

        OTExtensionWithMatrix *ot_ext = new OTExtensionWithMatrix(rP, ot_role);
        BitVector receiverInput(nOTs);
        if (P.my_num() == RECEIVER_P)
        {
            idtype idx;
            for (size_t i = 0; i < params.numBins(); i++)
            {
                if (!cuckoo.mBins[i].isEmpty())
                {
                    idx = smallids[cuckoo.mBins[i].idx()];
                    // std::cout << idx << " | ";
                    receiverInput.set_word(i, idx);
                    // std::cout << receiverInput.get_word(i) << std::endl;
                }
            }
            // std::cout << receiverInput.str() << std::endl;
            // receiverInput.randomize(G);
        }
        // cout << receiverInput.str() << flush;
        cout << "Running " << nOTs << " OT extensions\n"
             << flush;

        cout << "Initialize OT Extension\n";
        timeval OTextstart, OTextend;
        gettimeofday(&OTextstart, NULL);

        ot_ext->init(baseReceiverInput,
                     bot.sender_inputs, bot.receiver_outputs);
        ot_ext->transfer(nOTs, receiverInput, 1);
        // ot_ext.check();
        bot.extend_length();

        // print
        // for (int i = 0; i < nOTs; i++)
        // {
        //     if (ot_role == SENDER)
        //     {
        //         // send both inputs over
        //         cout << bot.sender_inputs[i][0].str() << " | " << bot.sender_inputs[i][1].str() << std::endl;
        //     }
        //     else
        //     {
        //         cout << receiverInput[i] << ": " << bot.receiver_outputs[i].str() << std::endl;
        //     }
        // }
        bot.check();

        gettimeofday(&OTextend, NULL);
        double totaltime = timeval_diff(&OTextstart, &OTextend);
        cout << "Time for OTExt (" << role_to_str(ot_role) << "): " << totaltime / 1000000 << endl
             << flush;

        octetStream cs, cs2;
        // caculate oprf
        if (P.my_num() == RECEIVER_P)
        {
            // vector<BitVector> r_fs(params.numBins());
            // receive oprf result
            P.receive_player(1 - RECEIVER_P, cs);
            vector<string> s_fs;
            idtype mm = m * 3;
            BitVector f_temp;
            for (size_t i = 0; i < mm; i++)
            {
                f_temp.unpack(cs);
                s_fs.push_back(f_temp.str());
                // std::cout << f_temp.str() << std::endl;
            }
            std::sort(s_fs.begin(), s_fs.end());

            // compare to find intersection set
            BitVector key, temp;
            string strkey;
            key.resize(sizeof(__m128i) << 3);
            idtype inter_id;
            vector<idtype> inter_ids;
            for (unsigned int i = 0; i < params.numBins(); i++)
            {
                if (!cuckoo.mBins[i].isEmpty())
                {
                    // std::cout << i << ": ";
                    key.assign_zero();
                    // get oprf
                    for (unsigned int j = 0; j < l; j++)
                    {
                        temp.assign_bytes((char *)ot_ext->get_receiver_output(i * l + j), sizeof(__m128i));
                        // cout << temp.str() << endl;
                        key.add(temp);
                    }
                    // r_fs[i] = key;
                    // find same element
                    strkey = key.str();
                    bool found = std::binary_search(s_fs.begin(), s_fs.end(), strkey);
                    if (found)
                    {
                        inter_id = smallids[cuckoo.mBins[i].idx()];
                        // cout << inter_id << ": " << strkey << endl;
                        inter_ids.push_back(inter_id);
                    }
                    // cout << smallids[cuckoo.mBins[i].idx()] << " " << r_fs[i].str() << endl;
                }
            }
            std::sort(inter_ids.begin(), inter_ids.end());
            idtype num = inter_ids.size();
            proc.Proc->public_file << num << "\n";
            cs2.store(num);
            size_t i = 0;
            for (const idtype &inter_id : inter_ids)
            {
                cs2.store(inter_id);
                proc.Proc->public_file << inter_id << "\n";
                // proc.Proc->public_output << inter_id << "\n";
            }
            P.send_to(1 - RECEIVER_P, cs2);
            // open result to sender
        }
        else // sender
        {
            BitVector key, temp;
            idtype id;
            vector<BitVector> fs;
            // vector<vector<BitVector>> fkx(params.numBins());
            key.resize(sizeof(__m128i) << 3);
            for (unsigned int i = 0; i < params.numBins(); i++)
            {
                // std::cout << "Bin #" << i << std::endl;
                std::array<vector<BitVector>, 2> outs;
                ot_ext->get_sender_output128i(outs, i * l, l);

                // for (size_t jj = i * params.numBins(); jj < i * l + l; jj++)
                // {
                //     std::cout << outs[0][jj].str() << " " << outs[1][jj].str() << endl;
                // }

                for (unsigned int k = 0; k < sIdx.mBinSizes[i]; k++)
                {
                    key.assign_zero();
                    id = smallids[sIdx.mBins(i, k).idx()];
                    // cout << id << " | ";
                    for (unsigned int j = 0; j < l; j++)
                    {
                        // std::cout << (id & 0x1);
                        temp = outs[id & 0x1][j];
                        id = id >> 1;
                        key.add(temp);
                    }
                    fs.push_back(key);
                    // cout << "|   " << fkx[i][k].str() << endl;
                }
            }
            for (BitVector fk : fs)
            {
                fk.pack(cs);
            }
            P.send_to(RECEIVER_P, cs);
            P.receive_player(RECEIVER_P, cs2);
            idtype num, inter_id;
            cs2.get(num);
            proc.Proc->public_file << num << "\n";
            for (size_t i = 0; i < num; i++)
            {
                cs2.get(inter_id);
                proc.Proc->public_file << inter_id << "\n";
                // cout << inter_id << endl;
                // dest[i] = inter_id;
            }
        }
        proc.Proc->public_file.seekg(0);

        if (0)
        {
            for (size_t i = 0; i < args.size(); i++)
            {
                cout << args[i] << " ";
            }
            cout << endl;
            auto dest = &proc.C[args[1]];
            cout << proc.C.size() << " " << proc.C[args[1]].size() << " " << *dest << endl;
            for (size_t i = 0; i < args.back(); i++)
            {
                typename T::clear v = dest[i];
                cout << v << "  ";
            }
            cout << endl;
        }

        if (0)
        {
            BitVector receiver_output, sender_output;
            // char filename[1024];
            // sprintf(filename, RECEIVER_INPUT, P.my_num());
            // ofstream outf(filename);
            // receiverInput.output(outf, false);
            // outf.close();
            // sprintf(filename, RECEIVER_OUTPUT, P.my_num());
            // outf.open(filename);
            if (ot_role == SENDER)
            {

                // outf.close();

                // sprintf(filename, SENDER_OUTPUT, P.my_num(), i);
                // outf.open(filename);
                for (int j = 0; j < nOTs; j++)
                {
                    for (int i = 0; i < 2; i++)
                    {
                        sender_output.assign_bytes((char *)ot_ext->get_sender_output(i, j), sizeof(__m128i));
                        std::cout << sender_output.str() << "  ";
                        // sender_output.output(outf, false);
                    }
                    std::cout << std::endl;
                    // outf.close();
                }
            }
            else
            {
                for (unsigned int i = 0; i < nOTs; i++)
                {
                    receiver_output.assign_bytes((char *)ot_ext->get_receiver_output(i), sizeof(__m128i));
                    cout << receiverInput[i] << ": " << receiver_output.str() << std::endl;
                    // receiver_output.output(outf, false);
                }
            }
        }
        delete rP;
    }
}
#endif
